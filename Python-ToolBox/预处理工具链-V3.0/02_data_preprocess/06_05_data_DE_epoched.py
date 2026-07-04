"""
使用说明：直接终端运行即可
DE微分熵：情感计算和认知状态识别等深度学习任务中非常有效的特征，若任务是情感识别、疲劳监测或专注度分析，建议每个epoch按2s分段50%重叠步长

1.DE input：分段处理后的数据，即运行过06_03_data_epoched.py的csv文件
通常的流水线是：原始数据 -> 滤波 (Filter) → 伪迹处理 (ICA/极值点插值) → 分段 (Epoch) → 频段提取 (Bandpass) → 计算 DE
2.DE output: 输出可直接用于深度学习模型的输入,数据格式为(Epochs x Features)
 eg.特征维度: (429, 21) 表示有429个Epochs，每个epoch有21个Features
3.注意事项：建议不做标准化（05_data_scaler）直接对数据进行分段，再计算每个分段的微分熵；
若要进行标准化（zscore），也可保留DE在各频段上的信号波动特征，但数值量纲有变化，DE_standardized = DE_raw - ln(S_global)
深度学习模型在训练过程中会自动通过偏置项（Bias）来抵消这个偏移
"""
import pandas as pd
import numpy as np
from scipy.signal import butter, filtfilt
import os

# --- 核心算法函数 ---

def bandpass_filter(data, low, high, fs):
    """对信号进行带通滤波"""
    nyq = 0.5 * fs
    # 增加对数据长度的检查，防止数据过短导致滤波报错
    if len(data) <= 3 * 5:  # 5是滤波阶数
        return np.zeros_like(data)
    b, a = butter(5, [low/nyq, high/nyq], btype='band')
    return filtfilt(b, a, data)

def calculate_de(signal):
    """
    计算微分熵 (Differential Entropy)
    假设信号服从高斯分布，公式为: 1/2 * log(2 * pi * e * sigma^2)
    """
    var = np.var(signal, ddof=1)
    if var <= 0:
        return 0
    return 0.5 * np.log(2 * np.pi * np.exp(1) * var)

def calc_de_features(epoch_df, channels, fs, bands):
    """计算单个Epoch中所有通道在各个频带的DE值"""
    de_results = {}
    
    for chan in channels:
        if chan in epoch_df.columns and not epoch_df[chan].isnull().all():
            raw_signal = epoch_df[chan].dropna().values
            
            for band_name, (low, high) in bands.items():
                # 1. 频段滤波
                filtered_data = bandpass_filter(raw_signal, low, high, fs)
                # 2. 计算该频段下的 DE
                de_val = calculate_de(filtered_data)
                # 3. 存储特征，格式如: CH1_alpha
                de_results[f'{chan}_{band_name}'] = de_val
                
    return de_results

# --- Main ---

# --- 配置区 ---
files = [
    'Qinghui_Athena_cleaned_filtered_remove_epoched.csv',
    'Qinghui_S_cleaned_filtered_remove_epoched.csv',
]

CHANNELS = ['CH1', 'CH2', 'CH3', 'CH4']

# 定义深度学习常用的五个频段
BANDS = {
    'delta': (1, 4),
    'theta': (4, 8),
    'alpha': (8, 13),
    'beta': (13, 30),
    'gamma': (30, 45)
}
# --- 配置结束 ---

print("开始处理分段数据的微分熵 (DE)...")

for file in files:
    if not os.path.exists(file):
        print(f"跳过不存在的文件: {file}")
        continue
        
    df = pd.read_csv(file)
    # 从分段数据的时间列重新获取采样率 (取前两个点的差值即可)
    sample_times = df['time'].unique()
    fs = 1 / np.mean(np.diff(sample_times))
    
    all_results = []
    
    # 按照 epoch_id 遍历每一段数据
    for epoch_id, epoch_df in df.groupby('epoch_id'):
        # 计算该 Epoch 下的所有通道、所有频段的 DE
        de_features = calc_de_features(epoch_df, CHANNELS, fs, BANDS)
        
        current_result = {'epoch_id': epoch_id}
        current_result.update(de_features)
        all_results.append(current_result)

    # 转化为 DataFrame
    results_df = pd.DataFrame(all_results)
    
    # 保存结果
    out_path = f"{os.path.splitext(file)[0]}_DE.csv"
    results_df.to_csv(out_path, index=False)
    
    print(f"处理完成: {file} -> {out_path}")
    print(f"特征维度: {results_df.shape} (Epochs x Features)")

print("\nDE特征提取结束")