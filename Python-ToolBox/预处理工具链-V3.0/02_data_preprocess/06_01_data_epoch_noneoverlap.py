import pandas as pd
import numpy as np
import os

# --- epoch函数 ---

def create_epochs(df, fs, window_sec=1.0):
    """
    将连续的EEG数据切割成指定时长的epochs
    为了方便保存, 整理成csv, 如有需要可以通过epoch_id重新由(samples, channels)→(segments, samples, channels) 
    Parameter: windows_sec指切割段的时间长度
    Return:含'epoch_id'、'time_in_epoch'列的新表
    """
    samples_per_epoch = int(window_sec * fs)
    total_samples = len(df)
    
    # 计算可以创建多少个完整的epoch
    num_epochs = total_samples // samples_per_epoch
    # 舍弃末尾不足一个epoch的数据
    df_trimmed = df.iloc[:num_epochs * samples_per_epoch].copy()

    # 创建epoch_id列，标记每个点属于哪个epoch
    df_trimmed['epoch_id'] = np.repeat(np.arange(num_epochs), samples_per_epoch)
    # # 创建每个epoch内的相对时间戳
    # time_vector = df_trimmed['time'].iloc[:samples_per_epoch].values
    # df_trimmed['time_in_epoch'] = np.tile(time_vector - time_vector[0], num_epochs)
    
    return df_trimmed

# ---Main---

# 在这里添加需要处理的csv
files_to_process = [
    'Qinghui_Athena_cleaned_filtered_remove_std.csv',
    'Qinghui_S_cleaned_filtered_remove_std.csv',
]

print("开始进行数据分段...")

for file_path in files_to_process:
    # if not os.path.exists(file_path):
    #     print(f"\n文件 '{file_path}' 不存在。")
    #     continue

    print(f"\n正在处理: {file_path}")
    df = pd.read_csv(file_path)

    # 从时间列重新计算采样率
    fs = 1 / np.mean(np.diff(df['time']))
    # print(f"计算采样率: {fs:.2f} Hz")
    
    # 分段，默认切割为1s的epoch
    epoched_df = create_epochs(df, fs, window_sec=1.0)
    
    # 保存处理后的csv
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}_epoched{ext}"
    epoched_df.to_csv(output_path, index=False)
    
    print(f"分段完成，保存→{output_path}")
    print(f"共有{epoched_df['epoch_id'].nunique()}个epochs")


print("\n所有csv分段完成")