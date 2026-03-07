import pylsl
import numpy as np
from scipy.signal import find_peaks, butter, filtfilt
from collections import deque
# 自定义参数
WINDOW_SIZE_SEC = 10  # 窗口大小(s)
FS_TARGET = 64        # 采样频率
SPO2_WINDOW_SIZE = 64 # SpO2滑动平均窗口大小
# 定义滤波器
def butter_bandpass(lowcut, highcut, fs, order=3):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    if low <= 0 or low >= 1 or high <= 0 or high >= 1:
        print(f"警告：归一化截止频率超出范围！low={low}, high={high}, fs={fs}")
        return None, None
    b, a = butter(order, [low, high], btype='band')
    return b, a
def bandpass_filter(data, lowcut, highcut, fs, order=3):
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    if b is None or a is None:
        return data  
    if len(data) <= order * 3:
        return data
    return filtfilt(b, a, data)
def calculate_spo2(ir_raw, red_raw, ir_filt, red_filt):
    """
    根据红光和红外光的AC/DC分量计算SpO2
    """
    try:
        # AC分量和DC分量
        ir_ac = np.std(ir_filt)
        red_ac = np.std(red_filt)
        ir_dc = np.mean(ir_raw)
        red_dc = np.mean(red_raw)
        # 计算R值
        R = (red_ac / red_dc) / (ir_ac / ir_dc)
        SpO2 = 100.67 - 9.14 * abs(R)  
        return SpO2
    except ZeroDivisionError:
        return None
# 查找PPG数据流
print("正在查找 PPG 数据流...")
streams = pylsl.resolve_stream('type', 'PPG')
streams_headon = pylsl.resolve_stream('type', 'HsiPrec')
print("已连接到PPG数据流。")
inlet = pylsl.stream_inlet(streams[0])
inlet_headon = pylsl.stream_inlet(streams_headon[0])
# 初始化滑动窗口
ir_buffer = deque(maxlen=int(WINDOW_SIZE_SEC * FS_TARGET))      # 红外信号缓冲区
red_buffer = deque(maxlen=int(WINDOW_SIZE_SEC * FS_TARGET))     # 红光信号缓冲区
time_buffer = deque(maxlen=int(WINDOW_SIZE_SEC * FS_TARGET))    # 时间戳缓冲区
spo2_buffer = deque(maxlen=SPO2_WINDOW_SIZE)                    # SpO2滑动窗口
while True:
    sample, timestamp_us = inlet.pull_sample(timeout=1.0)
    sample_headon, timestamp_us_headon = inlet_headon.pull_sample(timeout=1.0)
    # 仅在两个流都有效时才继续
    if sample is not None and sample_headon is not None:
        # print('HeadOn:', sample_headon) # 调试用
        timestamp = pylsl.local_clock()
        ambient, ir_signal, red_signal = sample[0], sample[1], sample[2]
        # 去除环境光干扰
        ir_signal_cleaned = ir_signal - ambient
        red_signal_cleaned = red_signal - ambient
        # 添加新数据到滑动窗口
        ir_buffer.append(ir_signal_cleaned)
        red_buffer.append(red_signal_cleaned)
        time_buffer.append(timestamp)
        # 仅当窗口填满后才开始处理
        if len(ir_buffer) >= int(WINDOW_SIZE_SEC * FS_TARGET * 0.9):
            ir_array = np.array(ir_buffer)
            red_array = np.array(red_buffer)
            time_array = np.array(time_buffer)
            # 计算实际采样频率
            if len(time_array) > 1:
                # 使用总时长计算
                fs = len(time_array) / (time_array[-1] - time_array[0])
            else:
                fs = FS_TARGET
            if fs == 0:
                continue
            # sample_headon都为4.0，重新佩戴
            if sample_headon==[4.0, 4.0, 4.0, 4.0]:
                spo2_avg=0.0
                print("信号质量不佳，请重新佩戴设备")
                print(f"{SPO2_WINDOW_SIZE}个数据的平均SpO2: {spo2_avg:.2f} %")
            else:
                # 佩戴质量好，正常计算
                ir_filt = bandpass_filter(ir_array, 0.5, 4, fs)
                red_filt = bandpass_filter(red_array, 0.5, 4, fs)

                # 计算spo2
                try:
                    SpO2 = calculate_spo2(ir_array, red_array, ir_filt, red_filt)
                    
                    if SpO2 is not None:
                        spo2_buffer.append(SpO2)
                        if len(spo2_buffer) >= SPO2_WINDOW_SIZE:
                            spo2_avg = np.mean(spo2_buffer)
                            print(f"{SPO2_WINDOW_SIZE}个数据的平均SpO2: {spo2_avg:.2f} %")

                except Exception as e:
                    print(f"处理时发生错误: {e}")