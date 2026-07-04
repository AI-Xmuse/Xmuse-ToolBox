"""
对连续数据进行psd计算，可以不用分段，使用分段数据计算psd可能会降低分辨率
"""

import pandas as pd
import numpy as np
from scipy.signal import welch
import os

def calc_psd(df, channels, fs):
    """计算平均功率谱(PSD)"""
    all_powers = []
    freqs = None
    win_samples = int(2 * fs)

    for chan in channels:
        if chan in df.columns:
            data = df[chan].dropna()
            if len(data) >= win_samples:
                f, p = welch(data, fs, nperseg=win_samples)
                if freqs is None:
                    freqs = f
                all_powers.append(p)
            
    if not all_powers:
        return None, None
    
    return freqs, np.mean(all_powers, axis=0)

def get_band_powers(freqs, psd, bands_to_extract, all_bands_definitions):
    """根据传入的列表，提取指定频带的相对功率"""
    total_p = np.sum(psd)
    band_p = {}
    
    for name in bands_to_extract:
        # 从“菜单”字典里查找频带的定义
        low, high = all_bands_definitions[name]
        mask = (freqs >= low) & (freqs <= high)
        p = np.sum(psd[mask])
        band_p[name] = p / total_p if total_p > 0 else 0
        
    return band_p

# ---Main---

# --- 配置区 ---
files = [
    'Qinghui_Athena_cleaned_filtered_remove_std.csv',
    'Qinghui_S_cleaned_filtered_remove_std.csv',
]
CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']

# 定义所有可选的频带
ALL_BANDS = {
    'Delta': (0.5, 4), 'Theta': (4, 8), 'Alpha': (8, 12), 'Alpha1': (8, 10),
    'Alpha2': (10, 12), 'Beta1': (12, 15), 'Beta2': (15, 20), 'Gamma1': (30, 60)
}

# 2. 在这里选择需要提取的频带
BANDS_TO_EXTRACT = ['Delta', 'Theta', 'Alpha', 'Beta1', 'Beta2']
#-------

print("开始处理PSD...")

for file in files:
    df = pd.read_csv(file)
    fs = 1 / np.mean(np.diff(df['time']))
    
    freqs, psd = calc_psd(df, CHANNELS, fs)
    
    # 将选择的频带列表和总菜单都传入函数
    band_powers = get_band_powers(freqs, psd, BANDS_TO_EXTRACT, ALL_BANDS)
    
    results = pd.DataFrame({'frequency': freqs, 'power': psd})
    for name, power in band_powers.items():
        results[f'{name}_rel_power'] = power
        
    out_path = f"{os.path.splitext(file)[0]}_psd.csv"
    results.to_csv(out_path, index=False)

print("处理结束")