import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
import os

# 滤波器函数，最好不要改会出错
def highpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='high', analog=False)
    return filtfilt(b, a, data)

def lowpass_filter(data, cutoff, fs, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    return filtfilt(b, a, data)

def notch_50hz_filter(data, fs, order=5):
    nyq = 0.5 * fs
    low, high = 49 / nyq, 51 / nyq
    b, a = butter(order, [low, high], btype='bandstop')
    return filtfilt(b, a, data)


# ---Main----
"""
如果单个通道数据质量不佳, 出现NaN, 导致滤波出错
主函数有两种校正方法: 1.出现NaN的时间点由上下数据点插值; 2.若滤波还是导致单通道出错置空NaN,会由临近通道插值坏道
"""
files_to_process = [
    'Qinghui_Athena_cleaned.csv',
    'Qinghui_S_cleaned.csv',
]

HP_CUTOFF = 0.5
LP_CUTOFF = 45
EEG_CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']
print("开始滤波...")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n csv'{file_path}'不存在")
        continue

    print(f"\n正在处理: {file_path}")
    df = pd.read_csv(file_path)

    fs = 1 / np.mean(np.diff(df['time'].dropna()))
    # print(f"采样率: {fs:.2f} Hz")

    # ---Filtering---
    filtered_results = {}
    print("滤波所有通道...")
    for chan in EEG_CHANNELS:
        if chan in df.columns and not df[chan].isnull().all():
            signal_to_filter = df[chan].interpolate(method='linear').bfill().ffill()
            original_signal = signal_to_filter.values
            
            # 应用滤波器
            filtered_signal = highpass_filter(original_signal, HP_CUTOFF, fs)
            filtered_signal = lowpass_filter(filtered_signal, LP_CUTOFF, fs)
            filtered_signal = notch_50hz_filter(filtered_signal, fs)
            
            filtered_results[chan] = filtered_signal
        else:
            filtered_results[chan] = None # 标记此通道为空或不存在

    # ---Check：插值滤波失败的坏导---
    print("检查坏导中...")
    for i, chan in enumerate(EEG_CHANNELS):
        result_signal = filtered_results.get(chan)

        # 检查滤波是否失败: 结果为None或包含NaN
        if result_signal is None or np.isnan(result_signal).any():
            print(f"通道{chan}滤波失败，使用邻近通道插值修复")
            
            # 寻找有效的邻居通道
            left_neighbor_data = None
            if i > 0: # 判断坏导是否为第一个通道
                prev_chan = EEG_CHANNELS[i-1]
                if filtered_results.get(prev_chan) is not None and not np.isnan(filtered_results[prev_chan]).any():
                    left_neighbor_data = filtered_results[prev_chan]

            right_neighbor_data = None
            if i < len(EEG_CHANNELS) - 1: # 判断坏导是否为最后一个通道
                next_chan = EEG_CHANNELS[i+1]
                if filtered_results.get(next_chan) is not None and not np.isnan(filtered_results[next_chan]).any():
                    right_neighbor_data = filtered_results[next_chan]

            # 根据邻居情况插值
            if left_neighbor_data is not None and right_neighbor_data is not None:
                df[chan] = (left_neighbor_data + right_neighbor_data) / 2
                print(f"使用{EEG_CHANNELS[i-1]} & {EEG_CHANNELS[i+1]} 的平均值修复{chan}")
            elif left_neighbor_data is not None: # 末道
                df[chan] = left_neighbor_data
                print(f"使用 {EEG_CHANNELS[i-1]}的数据修复了{chan}")
            elif right_neighbor_data is not None: # 首道
                df[chan] = right_neighbor_data
                print(f"使用 {EEG_CHANNELS[i+1]}的数据修复了{chan}")
            else:
                df[chan] = np.nan # 如果没有好邻居，只能置NaN
                print(f"无法修复 {chan}，无可用的邻近通道")
        else:
            # 滤波成功，写回数据
            df[chan] = result_signal

    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_filtered{ext}"
    df.to_csv(output_path, index=False)
    
    print(f"滤波完成，保存→{output_path}")

print("\n所有csv滤波处理完成")