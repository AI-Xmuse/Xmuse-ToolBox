import pandas as pd
import numpy as np
import os

# --- epoch函数 ---

def create_epochs(df, fs, window_sec=1.0, overlap_rate=0.0):
    """
    将连续的EEG数据切割成指定时长的epochs，支持重叠时间窗
    Parameter: 
        window_sec: 切割段的时间长度
        overlap_rate: 重叠程度 (0.0 ~ 1.0)，例如 0.5 表示 50% 重叠
    Return: 含'epoch_id'列的新表
    """
    samples_per_epoch = int(window_sec * fs)
    # 计算步长：如果重叠 0.5，步长就是窗口长度的一半
    step_size = int(samples_per_epoch * (1 - overlap_rate))
    
    # 确保步长至少为1个采样点
    if step_size < 1:
        step_size = 1

    total_samples = len(df)
    epochs_list = []
    start_idx = 0
    epoch_id = 0

    # 滑动窗口切片
    while start_idx + samples_per_epoch <= total_samples:
        # 提取当前片段并添加 epoch_id
        epoch_df = df.iloc[start_idx : start_idx + samples_per_epoch].copy()
        epoch_df['epoch_id'] = epoch_id
        
        epochs_list.append(epoch_df)
        
        # 按步长滑动
        start_idx += step_size
        epoch_id += 1

    # 合并所有片段
    if not epochs_list:
        return pd.DataFrame()
        
    return pd.concat(epochs_list, ignore_index=True)

# ---Main---

# --- 配置区 ---
files_to_process = [
    'Qinghui_Athena_cleaned_filtered_remove_std.csv',
    'Qinghui_S_cleaned_filtered_remove_std.csv',
]

WINDOW_SEC = 1.0    # 窗口长度（秒）
OVERLAP_RATE = 0.5  # 重叠程度（0.0为不重叠，0.5为重叠一半）
# --- 配置结束 ---

print(f"开始进行数据分段 (分段间重叠: {OVERLAP_RATE*100}%)...")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n文件 '{file_path}' 不存在，跳过。")
        continue

    print(f"\n正在处理: {file_path}")
    df = pd.read_csv(file_path)

    # 从时间列重新计算采样率
    fs = 1 / np.mean(np.diff(df['time']))
    
    # 分段，传入配置参数
    epoched_df = create_epochs(df, fs, window_sec=WINDOW_SEC, overlap_rate=OVERLAP_RATE)
    
    if epoched_df.empty:
        print("数据过短，无法生成有效 Epoch")
        continue

    # 保存处理后的csv
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_epoched{ext}"
    epoched_df.to_csv(output_path, index=False)
    
    print(f"分段完成，保存→{output_path}")
    print(f"共有{epoched_df['epoch_id'].nunique()}个epochs")


print("\n所有csv分段完成")