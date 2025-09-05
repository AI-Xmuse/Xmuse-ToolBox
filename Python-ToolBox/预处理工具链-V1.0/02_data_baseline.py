import pandas as pd
import numpy as np
import os

# 基线校正函数定义
def correct_dc_offset(df, offset_val=800, channels=None):
    """
    方法1：DC校正，直接减去固定值800
    """
    df_corrected = df.copy()
    if channels is None:
        channels = df.columns
    for chan in channels:
        if chan in df_corrected.columns:
            df_corrected[chan] = df_corrected[chan] - offset_val
            
    return df_corrected

def correct_baseline_channelwise(df, baseline_window_sec, fs, channels=None):
    """
    方法2：通道独立基线校正，减去各自通道的基线期均值
    """
    df_corrected = df.copy()
    if channels is None:
        channels = df.columns
    # 将时间窗口转换为数据点索引
    start_point = int(baseline_window_sec[0] * fs)
    end_point = int(baseline_window_sec[1] * fs)
    end_point = min(end_point, len(df)) # 确保索引不越界
    for chan in channels:
        if chan in df_corrected.columns:
            # 计算该通道在基线期内的均值
            baseline_mean = df_corrected[chan].iloc[start_point:end_point].mean()
            # 从整个通道减去这个均值
            df_corrected[chan] = df_corrected[chan] - baseline_mean

    return df_corrected


# ---Main---
# 添加需要进行基线校正的csv (一般是清理后)
files_to_process = [
    'Qinghui_Athena_cleaned.csv',
    'Qinghui_S_cleaned.csv',
]

# 自定义参数
BASELINE_WINDOW = (0.0, 0.2)  # 基线期为数据最开始的200ms
EEG_CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']
print("开始进行基线校正...")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n 文件 '{file_path}' 不存在")
        continue

    print(f"\n正在处理: {file_path}")
    df = pd.read_csv(file_path)

    fs = 1 / np.mean(np.diff(df['time']))
    # df_new = correct_dc_offset(df, offset_val=800, channels=EEG_CHANNELS) # 基线校正:方法1
    df_new = correct_baseline_channelwise(df, BASELINE_WINDOW, fs, EEG_CHANNELS) # 基线校正:方法2
    
    # 保存处理后的文件
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_baseline{ext}"
    df_new.to_csv(output_path, index=False)
    print(f"保存→{output_path}")

print("\n所有csv基线校正处理完成")