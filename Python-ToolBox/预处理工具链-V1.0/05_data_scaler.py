import pandas as pd
import numpy as np
import os

# ---缩放函数---
def normalize_channel(data):
    """(Min-Max) 将数据归一化到 [0, 1] 区间"""
    min_val = data.min()
    max_val = data.max()
    return (data - min_val) / (max_val - min_val)

def standardize_channel(data):
    """(Z-Score) 将数据标准化为均值0，标准差1"""
    mean_val = data.mean()
    std_val = data.std()
    return (data - mean_val) / std_val


# ---Main---

# 在这里添加需要处理的csv(通常前处理都已完成)
files_to_process = [
    'Qinghui_Athena_cleaned_filtered_remove.csv',
    'Qinghui_S_cleaned_filtered_remove.csv',
]

# 设定要处理的EEG通道
EEG_CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']
print("开始进行数据缩放...")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n文件 '{file_path}' 不存在。")
        continue

    print(f"\n正在处理: {file_path}")
    df = pd.read_csv(file_path)

    for chan in EEG_CHANNELS:
        if chan in df.columns:
            # 默认使用zscore标准化
            processed_signal = standardize_channel(df[chan])

            # # Min-Max归一化
            # processed_signal = normalize_channel(df[chan])

            # 处理后写入
            df[chan] = processed_signal
        else:
            print(f"未找到 {chan}")

    # 保存处理后的csv
    base, ext = os.path.splitext(file_path)
    # 需要手动改一下输出文件名根据选择的缩放函数后缀
    output_path = f"{base}_std{ext}"  # std标准化；nml归一化
    df.to_csv(output_path, index=False)
    
    print(f"处理完成，保存→{output_path}")

print("\n所有文件处理完成")