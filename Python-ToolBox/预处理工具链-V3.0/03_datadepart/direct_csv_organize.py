import pandas as pd
import os

def organize_directdata(df, base_name):
    """
    direct输出的EEG数据清理: 只拆分data列
    """
    
    # 按 "PacketType" 给数据分组，比如所有 'ACC' 的数据会成为一组
    for packet_type, group in df.groupby("PacketType"):
    
        group_data = group.copy()
        
        # 1. 清理 "Data" 列：先去掉双引号，再按逗号拆分成多列
        split_data = group_data["Data"].str.replace('"', '').str.split(",", expand=True)
        
        # 2. 给新拆分出的列起个名字，比如 eeg_1, eeg_2, ...
        split_data.columns = [f"eeg_{i+1}" for i in range(split_data.shape[1])]
        
        # 3. 把原始的 "Timestamp" 和清理好的数据重新拼在一起
        result = pd.concat([group_data["Timestamp"], split_data], axis=1)
        
        # 准备新文件名，格式是：原文件名_类型_organized.csv
        # 比如：test1_ACC_organized.csv
        output_filename = f"{base_name}_{packet_type}.csv"
        
        #保存
        result.to_csv(output_filename, index=False)
        print(f"已生成 -> {output_filename}")


#---主函数---
# 在这里添加需要处理的文件名
files_to_process = [
    'test1.csv',
    'test2.csv',
]

print("---批量整理数据---")
for file_path in files_to_process:
    print(f"\n正在处理: {file_path}")
    
    original_df = pd.read_csv(file_path)
    base_name = os.path.splitext(file_path)[0]
 
    organize_directdata(original_df, base_name)

print("\n所有csv整理完成")