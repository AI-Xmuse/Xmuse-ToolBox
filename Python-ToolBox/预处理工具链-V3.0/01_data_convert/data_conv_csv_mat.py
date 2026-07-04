import pandas as pd
import os
from scipy.io import savemat

def csv_to_mat(csv_path, output_path=None):
    """
    功能: 将csv转为.mat
    """
    # 自动在原文件名后添加.mat后缀
    if not output_path:
        output_path = os.path.splitext(csv_path)[0] + '.mat'
    
    # 读取csv文件
    df = pd.read_csv(csv_path)
    mat_data = {col: df[col].values for col in df.columns} # 将DataFrame转为matlab的字典格式{列名: 列数据}
    savemat(output_path, mat_data) # 保存.mat文件

# ---主函数---
# 在这里添加需要转换的csv
files_to_process = [
    'Qinghui_Athena.csv',
    'Qinghui_S.csv'
]
print("开始转换csv->mat...")

for file in files_to_process:
    csv_to_mat(file)

print("\n所有csv处理完成")