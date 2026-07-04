"""
采用时频分析滑动窗的思路计算动态的wpli，不需要基于分段数据，可以直接计算连续EEG，比data_wpli_epoched脚本更灵活，但计算时间更长
"""

import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt, hilbert
from itertools import combinations
import os

def bandpass_filter(data, low, high, fs):
    """对信号进行带通滤波"""
    nyq = 0.5 * fs
    b, a = butter(5, [low/nyq, high/nyq], btype='band')
    return filtfilt(b, a, data)

def calc_wpli_pairs(df_window, channels, fs, band):
    """计算单个数据窗内的所有wPLI值"""
    low, high = band
    wpli_results = {}
    analytic_signals = {}
    
    for chan in channels:
        if chan in df_window.columns and not df_window[chan].isnull().all():
            filtered_data = bandpass_filter(df_window[chan].dropna(), low, high, fs)
            analytic_signals[chan] = hilbert(filtered_data)
        
    for ch1, ch2 in combinations(channels, 2):
        if ch1 in analytic_signals and ch2 in analytic_signals:
            phase1 = np.angle(analytic_signals[ch1])
            phase2 = np.angle(analytic_signals[ch2])
            sin_diff = np.sin(phase1 - phase2)
            
            # 直接计算，如果分母为0会产生NaN或inf
            wpli = abs(np.mean(sin_diff)) / np.mean(abs(sin_diff))
            wpli_results[f'{ch1}-{ch2}'] = wpli
            
    return wpli_results

def calc_wpli_avg(wpli_pairs):
    """计算平均值，如果输入为空则返回NaN"""
    return np.mean(list(wpli_pairs.values()))

# ---Main---
# --- 配置区 ---
files = [
    'Qinghui_Athena_cleaned_filtered_remove_std.csv',
    'Qinghui_S_cleaned_filtered_remove_std.csv',
]
CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']
BAND = (8, 12)     # Alpha 频带
WIN_SEC = 2.0      # 窗长：2秒
STEP_SEC = 0.1     # 步长：0.1秒
# --- 配置结束 ---

print("开始处理动态wPLI...")

for file in files:
    # 直接执行，不作任何检查
    df = pd.read_csv(file)
    fs = 1 / np.mean(np.diff(df['time']))
    
    win_samples = int(WIN_SEC * fs)
    step_samples = int(STEP_SEC * fs)
    
    all_results = []
    
    for i in range(0, len(df) - win_samples + 1, step_samples):
        window_df = df.iloc[i : i + win_samples]
        
        wpli_pairs = calc_wpli_pairs(window_df, CHANNELS, fs, BAND)
        avg_wpli = calc_wpli_avg(wpli_pairs)
        
        window_time = window_df['time'].iloc[win_samples // 2]
        
        current_result = {'time': window_time, 'avg_wpli': avg_wpli}
        current_result.update(wpli_pairs)
        all_results.append(current_result)

    results_df = pd.DataFrame(all_results)
    
    band_name = f"{BAND[0]}-{BAND[1]}Hz"
    out_path = f"{os.path.splitext(file)[0]}_dyn_wpli_{band_name}.csv"
    results_df.to_csv(out_path, index=False)

print("处理结束")