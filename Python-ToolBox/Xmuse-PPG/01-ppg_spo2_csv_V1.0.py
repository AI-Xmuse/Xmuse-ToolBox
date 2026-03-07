import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
# 定义带通滤波器
def butter_bandpass(lowcut, highcut, fs, order=3):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a
def butter_bandpass_filter(data, lowcut, highcut, fs, order=3):
    b, a = butter_bandpass(lowcut, highcut, fs, order)
    y = filtfilt(b, a, data)
    return y
# 清理和预处理
columns_to_keep = ['timestamps', 'ppg_1', 'ppg_2', 'ppg_3']
try:
    data = pd.read_csv('exp1.csv', usecols=columns_to_keep) #在这里修改需要处理的csv文件名
except Exception as e:
    print(f"错误:读取CSV文件失败。 {e}")
    exit()
data.dropna(subset=['ppg_1', 'ppg_2', 'ppg_3'], inplace=True)
data.reset_index(drop=True, inplace=True)
data.rename(columns={
    'timestamps': 'time_us',
    'ppg_1': 'ambient',
    'ppg_2': 'ir',
    'ppg_3': 'red'
}, inplace=True)
time_us = data['time_us'].values
time = (time_us - time_us[0]) / 1e6
ambient = data['ambient'].values
ir = data['ir'].values
red = data['red'].values
fs = 1 / np.mean(np.diff(time))
# 去除环境光干扰
ir_cleaned = ir - ambient
red_cleaned = red - ambient
# 带通滤波（0.5 - 4 Hz）
ir_filt = butter_bandpass_filter(ir_cleaned, 0.5, 4, fs)
red_filt = butter_bandpass_filter(red_cleaned, 0.5, 4, fs)
# 计算AC和DC分量
ir_ac = np.std(ir_filt)
ir_dc = np.mean(ir_filt)
red_ac = np.std(red_filt)
red_dc = np.mean(red_filt)
# 计算比率R
R_raw = (red_ac / red_dc) / (ir_ac / ir_dc)
print(f'比率 R: {abs(R_raw):.4f}')
SpO2 = 106.67-9.14*abs(R_raw) 
SpO2 = min(SpO2, 100.0)
print(f'血氧饱和度(SpO2): {SpO2:.2f} %')