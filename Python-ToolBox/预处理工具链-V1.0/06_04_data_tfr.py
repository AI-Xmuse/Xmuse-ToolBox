import pandas as pd
import numpy as np
import os
import mne

def calc_tfr_avg(df, channels, fs):
    """
    使用小波变换计算多个通道的平均时频能量矩阵。
    """
    # 准备数据：MNE需要 (n_channels, n_times) 格式
    data = df[channels].values.T
    
    # MNE的小波变换函数需要一个 (n_epochs, n_channels, n_times) 的3D数组
    # 我们这里是连续数据，所以可以看作是1个很长的Epoch
    data_3d = np.expand_dims(data, axis=0)
    
    # 定义要分析的频率范围和每个频率对应的小波周期数
    freqs = np.arange(1., 41., 1.) # 分析 1-40 Hz
    n_cycles = freqs / 2. # 低频周期少(时间分辨率高)，高频周期多(频率分辨率高)
    
    # 使用MNE的tfr_array_morlet函数进行小波变换
    power_3d = mne.time_frequency.tfr_array_morlet(
        data_3d,
        sfreq=fs,
        freqs=freqs,
        n_cycles=n_cycles,
        output='power'
    )
    
    # power_3d 的形状是 (1, n_channels, n_freqs, n_times)，我们需要平均 n_channels
    # 先去掉第一个维度，再对通道维度(axis=0)取平均
    avg_power = np.mean(power_3d[0], axis=0)
    
    return freqs, df['time'].values, avg_power

def calc_tfr_single(df, channel_name, fs):
    """
    使用小波变换计算单个通道的时频能量矩阵。
    """
    # 准备数据：(1, 1, n_times)
    data = df[[channel_name]].values.T
    data_3d = np.expand_dims(data, axis=0)
    
    freqs = np.arange(1., 41., 1.)
    n_cycles = freqs / 2.
    
    power_3d = mne.time_frequency.tfr_array_morlet(
        data_3d,
        sfreq=fs,
        freqs=freqs,
        n_cycles=n_cycles,
        output='power'
    )
    
    # power_3d 的形状是 (1, 1, n_freqs, n_times)，直接去掉多余维度
    power = np.squeeze(power_3d)
    
    return freqs, df['time'].values, power

# ---Main---
# --- 配置区 ---
files = [
    'Qinghui_Athena_cleaned_filtered_remove_std.csv',
    'Qinghui_S_cleaned_filtered_remove_std.csv',
]
CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']

# 当您选择“单个通道”模式时，下面的变量会被使用
CHANNEL_TO_ANALYZE = 'CH1'
# --- 配置结束 ---

print("开始处理时频分析...")

for file in files:
    print(f"\n处理: {os.path.basename(file)}")
    df = pd.read_csv(file)
    fs = 1 / np.mean(np.diff(df['time']))
    
    # 在下面两种方法中选择一种（取消您想用的那一种的注释）
    # # 方法1: 计算所有通道的平均时频能量 (默认启用)
    # freqs, times, power = calc_tfr_avg(df, CHANNELS, fs)
    # out_path = f"{os.path.splitext(file)[0]}_tfr_avg.csv"
    
    #方法2: 只计算单个指定通道的时频能量
    freqs, times, power = calc_tfr_single(df, CHANNEL_TO_ANALYZE, fs)
    out_path = f"{os.path.splitext(file)[0]}_tfr_{CHANNEL_TO_ANALYZE}.csv"

    # --- 保存结果 ---
    # 将2D能量矩阵转换为DataFrame，行是频率，列是时间
    results_df = pd.DataFrame(power, index=freqs, columns=times)
    results_df.index.name = 'frequency' # 给索引行命名
    
    results_df.to_csv(out_path)
    print(f"-> 完成, 结果已保存至 {os.path.basename(out_path)}")

print("\n处理结束")