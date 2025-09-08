
import pylsl
import time
import pandas as pd
import numpy as np
import os
import argparse
import keyboard
import logging
from datetime import datetime
from sklearn.linear_model import LinearRegression
from pathlib import Path
from typing import List, Optional, Union, Dict, Any


def setup_logging(log_dir: str):
    """配置日志系统，同时输出到控制台和文件"""
    # 创建日志目录
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    # 日志文件名
    log_filename = os.path.join(log_dir, f"collection_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    # 配置日志格式
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename),  # 写入文件
            logging.StreamHandler()  # 输出到控制台
        ]
    )
    return log_filename


def main():
    # --- 解析命令行参数 ---
    parser = argparse.ArgumentParser(description='LSL数据采集程序，用于采集EEG等生理信号数据')
    # 数据流设置
    parser.add_argument('--stream-types', nargs='+', default=["EEG"],help='需要采集的数据类型，例如 "EEG ACC GYRO PPG"')
    parser.add_argument('--custom-channels', nargs='+', default=["ch_1", "ch_2", "ch_3", "ch_4"],help='自定义通道名称，数量需与实际通道数匹配')
    # 采集参数
    parser.add_argument('--duration', type=int, default=None,help='数据采集时长（秒），不设置则无限采集直到手动停止')
    parser.add_argument('--lsl-timeout', type=float, default=5.0,help='LSL流查找的超时时间（秒）')
    parser.add_argument('--chunk-duration', type=float, default=0.05,help='数据块拉取的目标时长（秒）')
    parser.add_argument('--chunk-timeout', type=float, default=0.01,help='pull_chunk的超时时间（秒）')
    parser.add_argument('--dejitter', action='store_true', default=True,help='对时间戳进行线性回归去抖动')
    parser.add_argument('--no-dejitter', action='store_false', dest='dejitter',help='不对时间戳进行去抖动处理')
    # 保存设置
    parser.add_argument('--continuous-save', action='store_true', default=False,help='开启连续保存模式')
    parser.add_argument('--save-interval', type=int, default=5,help='连续保存模式下的保存间隔（秒）')
    parser.add_argument('--output-dir', default="signal_data",help='数据保存的根目录')
    args = parser.parse_args()
    # --- 配置参数 ---
    STREAM_TYPES: List[str] = args.stream_types
    COLLECTION_DURATION: Optional[int] = args.duration
    LSL_SCAN_TIMEOUT: float = args.lsl_timeout
    PULL_CHUNK_DURATION: float = args.chunk_duration
    PULL_CHUNK_TIMEOUT: float = args.chunk_timeout
    DEJITTER_TIMESTAMPS: bool = args.dejitter
    CONTINUOUS_SAVE: bool = args.continuous_save
    CONTINUOUS_SAVE_INTERVAL_S: int = args.save_interval
    CUSTOM_CHANNEL_NAMES: List[str] = args.custom_channels
    # --- 数据保存目录设置 ---
    COLLECTION_TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
    BASE_SAVE_DIR = os.path.join(args.output_dir, COLLECTION_TIMESTAMP)
    Path(BASE_SAVE_DIR).mkdir(parents=True, exist_ok=True)
    # 配置日志
    log_dir = os.path.join(BASE_SAVE_DIR, "logs")
    log_file = setup_logging(log_dir)
    logging.info(f"程序启动，数据将保存到: {os.path.abspath(BASE_SAVE_DIR)}")
    logging.info(f"日志文件将保存到: {os.path.abspath(log_file)}")
    # --- LSL 流初始化 ---
    inlets: Dict[str, pylsl.StreamInlet] = {}
    stream_details: Dict[str, Dict[str, Any]] = {}
    current_stream_data: Dict[str, Dict[str, List[Union[List[float], float]]]] = {}
    logging.info("\n--- 开始查找和初始化 LSL 数据流 ---")
    for s_type in STREAM_TYPES:
        logging.info(f"尝试查找 {s_type} 数据流...")
        try:
            streams = pylsl.resolve_byprop("type", s_type, timeout=LSL_SCAN_TIMEOUT)
            if streams:
                logging.info(f"已找到 {s_type} 数据流。")
                stream_info = streams[0]
                inlet = pylsl.StreamInlet(
                    stream_info,
                    max_chunklen=int(stream_info.nominal_srate() * PULL_CHUNK_DURATION)
                )
                inlets[s_type] = inlet
                nominal_srate = stream_info.nominal_srate()
                channel_count = stream_info.channel_count()
                if nominal_srate <= 0:
                    logging.warning(f"{s_type} 的名义采样率为 0 或未指定。默认设置为 256 Hz。")
                    nominal_srate = 256.0

                if len(CUSTOM_CHANNEL_NAMES) == channel_count:
                    ch_names = CUSTOM_CHANNEL_NAMES
                    logging.info(f"  使用自定义通道名称: {ch_names}")
                else:
                    ch_names = []
                    ch = stream_info.desc().child('channels').first_child()
                    for _ in range(channel_count):
                        ch_names.append(ch.child_value('label'))
                        ch = ch.next_sibling()
                    if not ch_names:
                        ch_names = [f'channel_{i + 1}' for i in range(channel_count)]
                    logging.info(f"  使用流定义的通道名称: {ch_names}")

                stream_details[s_type] = {
                    'channel_count': channel_count,
                    'nominal_srate': nominal_srate,
                    'channel_format': stream_info.channel_format(),
                    'channel_names': ch_names,
                    'filename': os.path.join(BASE_SAVE_DIR, f"{s_type}_signal.csv")
                }

                # 写入CSV头部
                header_df = pd.DataFrame(columns=["timestamp"] + ch_names)
                header_df.to_csv(stream_details[s_type]['filename'], index=False)
                logging.info(f"  {s_type} 流信息：通道数={channel_count}, 采样率={nominal_srate} Hz")
                logging.info(f"  {s_type} 数据将保存到: {stream_details[s_type]['filename']}")
                current_stream_data[s_type] = {'samples': [], 'timestamps': []}
            else:
                logging.warning(f"未找到 {s_type} 数据流。")
        except Exception as e:
            logging.error(f"查找 {s_type} 数据流时发生错误: {str(e)}", exc_info=True)
    if not inlets:
        logging.error("未找到任何主要数据流（如 EEG）。请确保设备已连接并处于运行状态。")
        return
    # --- 数据保存辅助函数 ---
    def _save_data_chunk(
            filename: Union[str, Path],
            samples: List[List[float]],
            timestamps: List[float],
            time_correction: float,
            dejitter: bool,
            ch_names: List[str],
            is_continuous_save: bool
    ) -> None:
        if not samples:
            return
        try:
            samples_np = np.array(samples)
            timestamps_np = np.array(timestamps)
            sample_count = len(samples)
            # 校正时间戳到本地系统时间
            timestamps_corrected = timestamps_np + time_correction
            if dejitter:
                # 线性回归去抖动
                X = np.atleast_2d(np.arange(0, len(timestamps_corrected))).T
                lr = LinearRegression()
                lr.fit(X, timestamps_corrected)
                timestamps_processed = lr.predict(X)
                logging.debug(f"对 {sample_count} 个样本进行了时间戳去抖动处理")
            # 合并并保存数据
            combined_data = np.c_[timestamps_processed, samples_np]
            df = pd.DataFrame(data=combined_data, columns=["timestamp"] + ch_names)
            if not Path(filename).exists() or not is_continuous_save:
                df.to_csv(filename, float_format='%.6f', index=False, mode='a' if is_continuous_save else 'w')
            else:
                df.to_csv(filename, float_format='%.6f', index=False, mode='a', header=False)
            logging.debug(f"已保存 {sample_count} 个样本到 {filename}")
        except Exception as e:
            logging.error(f"保存数据块时发生错误: {str(e)}", exc_info=True)
    # --- 主数据采集循环 ---
    try:
        logging.info("\n--- 开始记录数据 ---")
        logging.info("按 Ctrl+C 或 Q 键停止记录")
        start_time = time.time()
        last_save_time = start_time
        should_stop = False  # 结束标志
        total_samples_collected = {s_type: 0 for s_type in STREAM_TYPES}  # 统计每个流采集的样本数
        # 初始时间校正
        initial_time_correction = {}
        for s_type, inlet_obj in inlets.items():
            try:
                initial_time_correction[s_type] = inlet_obj.time_correction()
                logging.info(f"  {s_type} 初始 LSL 时间校正: {initial_time_correction[s_type]:.3f} 秒")
            except Exception as e:
                logging.error(f"获取 {s_type} 时间校正时出错: {str(e)}", exc_info=True)
                initial_time_correction[s_type] = 0.0
        # 注册Q键事件处理 - 用于结束录制
        def end_recording():
            nonlocal should_stop
            if not should_stop:
                logging.info("\n检测到Q键，准备结束录制...")
                should_stop = True
        keyboard.add_hotkey('q', end_recording)
        while True:
            # 检查是否需要停止录制
            if should_stop:
                logging.info("\n用户通过Q键结束记录。")
                break
            # 检查是否达到采集时长
            if COLLECTION_DURATION is not None:
                elapsed_time = time.time() - start_time
                if elapsed_time > COLLECTION_DURATION:
                    logging.info(f"\n已达到 {COLLECTION_DURATION} 秒的采集时长。")
                    break
            # 从每个数据流读取数据
            for s_type, inlet_obj in inlets.items():
                try:
                    nominal_srate = stream_details[s_type]['nominal_srate']
                    max_samples_to_pull = max(1, int(nominal_srate * PULL_CHUNK_DURATION))

                    samples, lsl_timestamps = inlet_obj.pull_chunk(timeout=PULL_CHUNK_TIMEOUT, max_samples=max_samples_to_pull)
                    if samples:
                        sample_count = len(samples)
                        total_samples_collected[s_type] += sample_count
                        current_stream_data[s_type]['samples'].extend(samples)
                        current_stream_data[s_type]['timestamps'].extend(lsl_timestamps)
                        # 每采集1000个样本记录一次信息（避免日志过多）
                        if total_samples_collected[s_type] % 1000 == 0:
                            logging.debug(f"{s_type} 已采集 {total_samples_collected[s_type]} 个样本")
                except pylsl.timeout_error:
                    pass  # 没有新数据，正常现象
                except Exception as e:
                    logging.error(f"处理 {s_type} 数据时出错: {str(e)}", exc_info=True)
                    continue
            # 连续保存模式
            if CONTINUOUS_SAVE and (time.time() - last_save_time) >= CONTINUOUS_SAVE_INTERVAL_S:
                logging.info(f"正在连续保存数据到 {BASE_SAVE_DIR}...")
                for s_type in STREAM_TYPES:
                    if s_type in inlets:
                        _save_data_chunk(
                            stream_details[s_type]['filename'],
                            current_stream_data[s_type]['samples'],
                            current_stream_data[s_type]['timestamps'],
                            initial_time_correction[s_type],
                            DEJITTER_TIMESTAMPS,
                            stream_details[s_type]['channel_names'],
                            is_continuous_save=True)
                        current_stream_data[s_type]['samples'] = []
                        current_stream_data[s_type]['timestamps'] = []
                last_save_time = time.time()
            time.sleep(0.001)
    except KeyboardInterrupt:
        logging.info("\n用户通过Ctrl+C中断记录。")
    except Exception as e:
        logging.error(f"发生意外错误: {str(e)}", exc_info=True)
    finally:
        # 移除键盘事件监听
        keyboard.unhook_all()
        logging.info("\n--- 数据采集完成，正在保存剩余数据 ---")
        for s_type in STREAM_TYPES:
            if s_type in inlets:
                sample_count = len(current_stream_data[s_type]['samples'])
                total_samples = total_samples_collected[s_type] + sample_count
                logging.info(f"  {s_type} 总共采集 {total_samples} 个样本")
                _save_data_chunk(
                    stream_details[s_type]['filename'],
                    current_stream_data[s_type]['samples'],
                    current_stream_data[s_type]['timestamps'],
                    initial_time_correction[s_type],
                    DEJITTER_TIMESTAMPS,
                    stream_details[s_type]['channel_names'],
                    is_continuous_save=False)
                logging.info(f"  {s_type} 数据已保存到: {os.path.abspath(stream_details[s_type]['filename'])}")
        # 记录程序结束信息
        elapsed_time = time.time() - start_time
        logging.info(f"所有数据保存完成。总采集时间: {elapsed_time:.2f} 秒")
        logging.info("程序正常退出。")
if __name__ == "__main__":
    main()
