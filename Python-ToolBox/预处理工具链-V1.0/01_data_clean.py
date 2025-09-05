"""
当前的方法仅针对4channel EEG数据，如果改动采集PRESET需要修改代码和函数
"""
import pandas as pd
import numpy as np
import os

def clean_eeg_frame(df: pd.DataFrame) -> pd.DataFrame:
    """EEG数据清理"""

    # 重命名列
    rename_map = {
        'timestamps': 'time',
        'eeg_1': 'CH1',
        'eeg_2': 'CH2',
        'eeg_3': 'CH3',
        'eeg_4': 'CH4'
    }
    required_cols_original = list(rename_map.keys())
    df_cleaned = df[required_cols_original].rename(columns=rename_map)

    # 删除EEG通道数据空行
    eeg_channels = ['CH1', 'CH2', 'CH3', 'CH4']
    df_cleaned.dropna(subset=eeg_channels, how='all', inplace=True)
    if df_cleaned.empty:
        return df_cleaned

    # 时间戳转换为0起始相对时间
    df_cleaned.reset_index(drop=True, inplace=True)
    df_cleaned['time'] = df_cleaned['time'] - df_cleaned['time'].iloc[0]
    
    return df_cleaned


# -----主函数-----
# 在这里添加需要处理的文件，当前为示例文件
files_to_process = [
    'Qinghui_Athena.csv',
    'Qinghui_S.csv',
]

print("开始批量处理EEG数据...")

for file_path in files_to_process:
    if not os.path.exists(file_path):
        print(f"\n 文件 '{file_path}' 不存在")
        continue
    print(f"\n 正在处理: {file_path}")

    #读取+清洗
    original_df = pd.read_csv(file_path, na_values=[''])
    cleaned_df = clean_eeg_frame(original_df)

    # 保存csv
    base_name, extension = os.path.splitext(file_path)
    output_path = f"{base_name}_cleaned{extension}"
    cleaned_df.to_csv(output_path, index=False)
    print(f"清理完成，已保存至→{output_path}")

    # # 计算并打印采样率
    # if len(cleaned_df) > 1:
    #     mean_interval = np.mean(np.diff(cleaned_df['time']))
    #     sampling_rate = 1 / mean_interval if mean_interval > 0 else 0
    #     print(f"计算出的平均采样率: {sampling_rate:.2f} Hz")
    # else:
    #     print("数据点不足，无法计算采样率。")

print("\n所有csv清洗完成")