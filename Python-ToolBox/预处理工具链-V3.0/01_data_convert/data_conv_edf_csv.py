import mne
import pandas as pd
import os

def edf_to_csv(raw_obj):
    """转换功能：将MNE的Raw对象转为Pandas的DataFrame"""
    data = raw_obj.get_data()
    channels = raw_obj.ch_names
    df = pd.DataFrame(data.T, columns=channels)
    df.insert(0, 'time', raw_obj.times)
    return df

# ---主函数---
# 在这里添加需要转格式的edf
files_to_process = [
    'exp1.edf',
    'exp2.edf',
    'exp3.edf'
]
print("正在转换edf->csv...")

for edf_path in files_to_process:
    # 用mne读edf
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False) # verbose=False不在控制台打印mne日志信息
    df = edf_to_csv(raw) #调用功能函数
    
    # 转换后的csv保存到当前路径
    base_name, _ = os.path.splitext(edf_path)
    csv_path = base_name + '.csv'
    df.to_csv(csv_path, index=False)
    
    print(f"转换完成: {edf_path} -> {csv_path}") # 注意！！！转换前μv，转换后v

print("\n所有edf转换完成")