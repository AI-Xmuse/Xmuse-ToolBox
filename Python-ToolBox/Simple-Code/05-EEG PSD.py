import numpy as np
import pandas as pd
from scipy import signal
from scipy.fftpack import fft
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
# 设置matplotlib支持中文显示
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'NSimSun', 'FangSong', 'KaiTi']  # 优先使用的中文字体列表
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 检查系统中可用的中文字体
def check_chinese_fonts():
    all_fonts = [f.name for f in fm.fontManager.ttflist]
    chinese_fonts = []
    for font in ['Microsoft YaHei', 'SimHei', 'SimSun', 'NSimSun', 'FangSong', 'KaiTi']:
        if font in all_fonts:
            chinese_fonts.append(font)
    if chinese_fonts:
        plt.rcParams['font.sans-serif'] = chinese_fonts
        print("使用中文字体:", chinese_fonts[0])
    else:
        print("警告：未找到中文字体，图表中的中文可能无法正常显示")
# 在程序开始时检查字体
check_chinese_fonts()

def loadEEGCSV(data_path: str, window: float = 1.0, frame: float = 0.5, sample_rate: int = 256, channels: int = 4):
    """
    Description: 加载csv文件
    -------------------------------
    Parameters:
    data_path: 输入的csv文件
    window:  窗的大小（单位：s），默认值为1.0
    frame:  帧的大小，即窗移的大小（单位：s），默认值为0.5
    sample_rate:  采样率的大小（单位：Hz），默认值为256
    channels: 期望的通道数，默认值为4
    """
    try:
        # load feature data
        df = pd.read_csv(data_path)
        print("CSV文件形状:", df.shape)
        print("CSV文件列名:", df.columns.tolist())
        df = df.iloc[:, 1:]

        FEATURE_NUM = int(window * sample_rate)
        FRAME_NUM = int(frame * sample_rate)
        # 读取所有列的数据
        data = df.values
        if channels != data.shape[1]:
            print(f"错误：期望{channels}个通道，但数据中有{data.shape[1]}个通道")
            return None
        j = 0
        X = np.zeros((int(data.shape[0] / FRAME_NUM), FEATURE_NUM, channels))
        for i in range(0, (data.shape[0] - FEATURE_NUM), FRAME_NUM):
            X[j, :, :] = data[i:i + FEATURE_NUM, :]
            j = j + 1
        return X
    except FileNotFoundError:
        print(f"文件 {data_path} 未找到")
        return None

def bandpass_filter(data, lowcut, highcut, fs, order=4):
    """
    带通滤波器
    Parameters:
    -----------
    data: 输入信号
    lowcut: 低频截止频率
    highcut: 高频截止频率
    fs: 采样率
    order: 滤波器阶数
    """
    nyquist = 0.5 * fs
    low = lowcut / nyquist
    if highcut is not None:
        high = highcut / nyquist
        b, a = signal.butter(order, [low, high], btype='band')
    else:
        b, a = signal.butter(order, low, btype='high')
    filtered_data = signal.filtfilt(b, a, data)
    return filtered_data

def compute_psd(data, fs):
    """
    计算功率谱密度
    Parameters:
    -----------
    data: 输入信号
    fs: 采样率
    Returns:
    -------
    freqs: 频率数组
    psd: 功率谱密度数组
    """
    return signal.welch(data, fs, nperseg=min(256, len(data)))

def compute_band_power(data, fs):
    """
    计算各频段的能量
    Parameters:
    -----------
    data: 输入信号
    fs: 采样率

    Returns:
    --------
    dict: 包含各个频段能量的字典
    """
    # 定义频段
    bands = {
        'delta': (1, 4),
        'theta': (4, 8),
        'alpha': (8, 13),
        'beta': (13, 30),
        'gamma': (30, 45)
    }
    # 计算功率谱密度
    freqs, psd = compute_psd(data, fs)
    # 计算各频段功率
    powers = {}
    for band_name, (low, high) in bands.items():
        # 找到频段对应的索引
        idx_band = np.logical_and(freqs >= low, freqs <= high)
        # 计算频段功率（积分）
        powers[band_name] = np.trapz(psd[idx_band], freqs[idx_band])
    return powers


def compute_relative_power(data, fs):
    """
    计算相对能量
    Parameters:
    -----------
    data: 输入信号
    fs: 采样率

    Returns:
    --------
    dict: 包含各个频段相对能量的字典
    """
    powers = compute_band_power(data, fs)
    total_power = sum(powers.values())
    if total_power == 0:
        return {band: 0.0 for band in powers.keys()}
    relative_powers = {}
    for band_name, power in powers.items():
        relative_powers[band_name] = power / total_power
    return relative_powers

def compute_spectral_entropy(data, fs):
    """
    计算频谱熵
    Parameters:
    -----------
    data: 输入信号
    fs: 采样率

    Returns:
    --------
    float: 频谱熵值
    """
    # 计算功率谱密度
    freqs, psd = compute_psd(data, fs)
    # 归一化PSD
    psd_norm = psd / np.sum(psd)
    # 计算熵值（去除零值以避免log2(0)）
    psd_norm = psd_norm[psd_norm > 0]
    entropy = -np.sum(psd_norm * np.log2(psd_norm))
    return entropy

def compute_hjorth_parameters(data):
    """
    计算Hjorth参数
    Parameters:
    -----------
    data: 输入信号
    Returns:
    --------
    tuple: (活动度, 移动度, 复杂度)
    """
    # 去除均值
    data = data - np.mean(data)
    # 活动度 - 信号方差
    activity = np.var(data)
    # 计算一阶差分
    d1 = np.diff(data)
    # 在差分点补充一个值保持长度一致
    # 因为np.diff会使数组长度减1，为了后续计算方便，这里补充最后一个差分的值
    d1 = np.append(d1, d1[-1])
    # 计算二阶差分
    d2 = np.diff(d1)
    d2 = np.append(d2, d2[-1])
    # 移动度 - 一阶差分信号方差与原始信号方差的比值的平方根
    mobility = np.sqrt(np.var(d1) / np.var(data))
    # 复杂度 - 二阶差分的移动度与一阶差分移动度的比值
    complexity = np.sqrt(np.var(d2) * np.var(data)) / np.var(d1)
    return activity, mobility, complexity

def analyze_eeg(data, fs):
    """
    综合分析EEG信号
    Parameters:
    -----------
    data: 输入信号
    fs: 采样率
    Returns:
    --------
    dict: 包含各种特征的字典
    """
    # 预处理：去除均值和线性趋势
    data = signal.detrend(data - np.mean(data))
    results = {}
    # 计算频段能量
    results['absolute_power'] = compute_band_power(data, fs)
    results['relative_power'] = compute_relative_power(data, fs)
    # 计算频谱熵
    results['spectral_entropy'] = compute_spectral_entropy(data, fs)
    # 计算Hjorth参数
    activity, mobility, complexity = compute_hjorth_parameters(data)
    results['hjorth'] = {
        'activity': activity,
        'mobility': mobility,
        'complexity': complexity
    }
    return results

def plot_power_spectrum(sample_data, fs, channel):
    """
    绘制功率谱密度图
    Parameters:
    -----------
    sample_data: 输入信号
    fs: 采样率
    channel: 通道编号
    """
    plt.figure(figsize=(10, 4))
    freqs, psd = compute_psd(sample_data, fs)
    plt.semilogy(freqs, psd)
    plt.title(f'通道 {channel + 1} 功率谱密度')
    plt.xlabel('频率 (Hz)')
    plt.ylabel('功率谱密度 (μV²/Hz)')
    plt.grid(True)
    plt.show()

if __name__ == '__main__':
    "输入"
    data_path = "EEG_signal.csv"
    X = loadEEGCSV(data_path)
    if X is not None and X.shape[0] > 0:
        print("数据形状:", X.shape)
        # 分析所有通道的第一个时间窗口
        print("\n各通道EEG信号分析结果:")
        print("=" * 50)
        for channel in range(X.shape[2]):
            print(f"\n通道 {channel + 1}:")
            print("-" * 30)
            sample_data = X[0, :, channel]
            fs = 256
            # 进行EEG分析
            analysis_results = analyze_eeg(sample_data, fs)
            print("\n绝对功率 (μV²):")
            for band, power in analysis_results['absolute_power'].items():
                print(f"{band}: {power:.6f}")
            print("\n相对功率 (%):")
            for band, power in analysis_results['relative_power'].items():
                print(f"{band}: {power * 100:.2f}%")
            print(f"\n频谱熵: {analysis_results['spectral_entropy']:.6f}")
            print("\nHjorth参数:")
            for param, value in analysis_results['hjorth'].items():
                print(f"{param}: {value:.6f}")
            # 绘制频谱
            plot_power_spectrum(sample_data, fs, channel)
    else:
        print("数据加载失败或数据为空")