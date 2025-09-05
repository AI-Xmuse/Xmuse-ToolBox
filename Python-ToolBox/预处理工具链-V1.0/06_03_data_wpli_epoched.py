"""
基于epoch的wpli计算
计算方法：“有符号虚部的平均值”和“虚部绝对值的平均值”的比值
wpli比plv更少受到伪影的影响，对0度和180度的伪影不敏感

使用时：必须基于分段的数据
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

def calc_wpli_pairs(df, channels, fs, band):
    """计算单个数据块(Epoch)中所有通道配对的wPLI值"""
    low, high = band
    wpli_results = {}
    analytic_signals = {}
    
    for chan in channels:
        if chan in df.columns and not df[chan].isnull().all():
            filtered_data = bandpass_filter(df[chan].dropna(), low, high, fs)
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
    """计算单个Epoch中所有连接值的平均值"""
    # 如果wpli_pairs为空，将返回NaN
    return np.mean(list(wpli_pairs.values()))

# ---Main---
# --- 配置区 ---
files = [
    'Qinghui_Athena_cleaned_filtered_remove_std_epoched.csv',
    'Qinghui_S_cleaned_filtered_remove_std_epoched.csv',
]
CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']
BAND = (8, 12) # Alpha 频带
# --- 配置结束 ---

print("开始处理分段数据的wPLI...")

for file in files:
    # 直接执行，不作任何检查
    df = pd.read_csv(file)
    fs = 1 / np.mean(np.diff(df['time'].unique()))
    
    all_results = []
    
    for epoch_id, epoch_df in df.groupby('epoch_id'):
        wpli_pairs = calc_wpli_pairs(epoch_df, CHANNELS, fs, BAND)
        avg_wpli = calc_wpli_avg(wpli_pairs)
        
        current_result = {'epoch_id': epoch_id, 'avg_wpli': avg_wpli}
        current_result.update(wpli_pairs)
        all_results.append(current_result)

    results_df = pd.DataFrame(all_results)
    
    band_name = f"{BAND[0]}-{BAND[1]}Hz"
    out_path = f"{os.path.splitext(file)[0]}_wpli_{band_name}.csv"
    results_df.to_csv(out_path, index=False)

print("处理结束")