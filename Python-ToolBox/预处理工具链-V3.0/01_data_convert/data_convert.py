import pandas as pd
import numpy as np
import mne
import os
from scipy.io import savemat

def edf_to_csv(edf_path, output_path=None):
    """edf转csv"""
    if not output_path:
        output_path = os.path.splitext(edf_path)[0] + '.csv'
    
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    raw.to_data_frame().to_csv(output_path, index=False)
    print(f"转换完成: {edf_path} -> {output_path}")

def csv_to_mne_raw(csv_path, sfreq, ch_names, ch_types='eeg'):
    """csv转mne的Raw对象"""
    df = pd.read_csv(csv_path)
    data_volts = df[ch_names].values.T * 1e-6 # .T转置，数值单位μv转换为v
    
    info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
    raw = mne.io.RawArray(data_volts, info, verbose=False)
    print(f"转换完成: {csv_path} -> MNE Raw 对象 (已在内存中)")
    return raw

def csv_to_mat(csv_path, output_path=None):
    """csv转mat"""
    if not output_path:
        output_path = os.path.splitext(csv_path)[0] + '.mat'
        
    df = pd.read_csv(csv_path)
    mat_data = {col: df[col].values for col in df.columns}
    savemat(output_path, mat_data)
    print(f"转换完成: {csv_path} -> {output_path}")


# ---主函数---
# 确保示例文件与脚本在同一目录

if __name__ == '__main__':

    # # 示例1: 转换单个EDF文件
    # edf_to_csv('exp1.edf')

    # # 示例2: 转换CSV为MNE对象 (需手动提供元数据)
    # sfreq = 250
    # eeg_channels = ['eeg_1', 'eeg_2', 'eeg_3', 'eeg_4']
    # raw_obj = csv_to_mne_raw('Qinghui_Athena.csv', sfreq, eeg_channels)
    # # raw_obj.plot() # 得到对象后可直接调用MNE方法

    # # 示例3: 转换CSV为MATLAB文件
    # csv_to_mat('Qinghui_Athena.csv')

    pass