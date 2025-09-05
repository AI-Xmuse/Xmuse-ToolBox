import pandas as pd
import numpy as np
import os
from typing import Tuple

def interpolate_outliers(df: pd.DataFrame, threshold: float) -> Tuple[pd.DataFrame, int]:
    """
    功能: 在给定的表中检测并插值超过阈值的点
    """
    eeg_channels = ['CH1', 'CH2', 'CH3', 'CH4']
    total_interpolated_count = 0

    for chan in eeg_channels:
        if chan not in df.columns:
            continue
        signal = df[chan]
        # 找到绝对值超过阈值的坏点
        bad_indices = np.abs(signal) > threshold
        bad_points_count = bad_indices.sum()

        if bad_points_count > 0:
            print(f"{chan}找到{bad_points_count}个极值点插值...")
            total_interpolated_count += bad_points_count
            
            # 坏点NaN，线性插值填充
            signal[bad_indices] = np.nan
            df[chan] = signal.interpolate(method='linear', limit_direction='both')
        else:
            print(f"{chan}无坏点")
            
    return df, total_interpolated_count


# ---Main---
# 自定义需要插值的csv(可以是滤波后的文件)
files_to_process = [
    'Qinghui_Athena_cleaned_filtered.csv',
    'Qinghui_S_cleaned_filtered.csv',
]

# 自定义振幅阈值(µV)
AMPLITUDE_THRESHOLD = 100

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n 文件'{file_path}'不存在")
        continue

    df = pd.read_csv(file_path)
    df_interpolated, num_fixed = interpolate_outliers(df, AMPLITUDE_THRESHOLD)
    
    # 有修改就保存为带后缀的新csv
    if num_fixed > 0:
        base, ext = os.path.splitext(file_path)
        output_path = f"{base}_remove{ext}"
        df_interpolated.to_csv(output_path, index=False)
        print(f"已保存至→'{output_path}'")
    continue
print("\n所有csv插值完成")