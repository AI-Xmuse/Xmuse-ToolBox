import pandas as pd
import os
import numpy as np
import argparse

def rename_eeg_columns(df):
    """将DataFrame中的eeg_1、eeg_2、eeg_3、eeg_4列名分别替换为TP9、AF7、AF8、TP10"""
    column_mapping = {
        'eeg_1': 'TP9',
        'eeg_2': 'AF7',
        'eeg_3': 'AF8',
        'eeg_4': 'TP10'
    }
    # 只重命名存在的列
    existing_columns = df.columns.tolist()
    columns_to_rename = {k: v for k, v in column_mapping.items() if k in existing_columns}
    if columns_to_rename:
        df = df.rename(columns=columns_to_rename)
        print(f"已替换列名: {columns_to_rename}")
    else:
        print("未找到需要替换的列名")
    return df

def correct_dc_offset(df, offset_val=800, channels=None):
    """方法1：DC校正，直接减去固定值"""
    df_corrected = df.copy()
    if channels is None:
        channels = df.columns
    for chan in channels:
        if chan in df_corrected.columns:
            df_corrected[chan] = df_corrected[chan] - offset_val
    return df_corrected

def correct_baseline_channelwise(df, baseline_window_sec, fs, channels=None):
    """方法2：通道独立基线校正，减去各自通道的基线期均值"""
    df_corrected = df.copy()
    if channels is None:
        channels = df.columns
    # 将时间窗口转换为数据点索引
    start_point = int(baseline_window_sec[0] * fs)
    end_point = int(baseline_window_sec[1] * fs)
    end_point = min(end_point, len(df))  # 确保索引不越界
    for chan in channels:
        if chan in df_corrected.columns:
            # 计算该通道在基线期内的均值
            baseline_mean = df_corrected[chan].iloc[start_point:end_point].mean()
            # 从整个通道减去这个均值
            df_corrected[chan] = df_corrected[chan] - baseline_mean
    return df_corrected

def main():
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(description='EEG数据处理：列名替换与基线校正')
    # 文件路径（可指定多个）
    parser.add_argument('--files', nargs='+', help='需要处理的CSV文件路径',default=['Processed_EEG_DEL.csv','processed_eeg_data.csv'])
    parser.add_argument('--baseline-method', type=int, default=2, choices=[1, 2],help='基线校正方法 (1: DC校正, 2: 通道独立基线校正，默认: 2)')
    parser.add_argument('--baseline-start', type=float, default=0.0,help='基线期起始时间(秒)，默认: 0.0')
    parser.add_argument('--baseline-end', type=float, default=0.2,help='基线期结束时间(秒)，默认: 0.2')
    parser.add_argument('--dc-offset', type=int, default=800,help='DC校正的偏移值，默认: 800')
    parser.add_argument('--channels', nargs='+', default=['TP9', 'AF7', 'AF8', 'TP10'],help=f'需要处理的通道列表，默认: TP9 AF7 AF8 TP10')
    # 解析参数
    args = parser.parse_args()
    # 显示参数信息
    print("===== 处理参数 =====")
    print(f"处理文件: {args.files}")
    print(f"基线校正方法: 方法{args.baseline_method}")
    print(f"基线期窗口: {args.baseline_start}s 到 {args.baseline_end}s")
    print(f"DC校正偏移值: {args.dc_offset}")
    print(f"处理通道: {args.channels}")
    print("===================\n")
    # 处理每个文件
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"\n⚠️ 文件 '{file_path}' 不存在，跳过处理")
            continue
        print(f"正在处理: {file_path}")
        # 1. 读取CSV文件
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            continue
        print(f"原始数据列名: {df.columns.tolist()}")
        # 2. 重命名EEG通道列
        df = rename_eeg_columns(df)
        print(f"重命名后的数据列名: {df.columns.tolist()}")
        # 3. 计算采样频率
        if 'time_diff' not in df.columns:
            print("❌ 数据中未找到'time_diff'列，无法计算采样频率，跳过该文件")
            continue
        try:
            fs = 1 / np.mean(np.diff(df['time_diff']))
            print(f"计算得到的采样频率: {fs:.2f} Hz")
        except Exception as e:
            print(f"❌ 计算采样频率失败: {e}，跳过该文件")
            continue
        # 4. 进行基线校正
        try:
            if args.baseline_method == 1:
                df_processed = correct_dc_offset(df, offset_val=args.dc_offset, channels=args.channels)
            else:
                baseline_window = (args.baseline_start, args.baseline_end)
                df_processed = correct_baseline_channelwise(df, baseline_window, fs, channels=args.channels)
        except Exception as e:
            print(f"❌ 基线校正失败: {e}，跳过该文件")
            continue
        # 5. 保存处理后的文件
        try:
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}_processed{ext}"
            df_processed.to_csv(output_path, index=False)
            print(f"✅ 处理完成，已保存到→{output_path}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
    print("\n所有文件处理完毕")


if __name__ == "__main__":
    main()
