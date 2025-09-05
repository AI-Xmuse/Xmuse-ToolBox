import pandas as pd
import numpy as np
import os
import argparse
import pathlib


# --- epoch函数 ---
def create_epochs(df, fs, window_sec=1.0):
    """
    将连续的EEG数据切割成指定时长的epochs
    Parameter: windows_sec指切割段的时间长度
    Return:含'epoch_id'列的新表和epoch数量
    """
    samples_per_epoch = int(window_sec * fs)
    total_samples = len(df)

    # 计算可以创建多少个完整的epoch
    num_epochs = total_samples // samples_per_epoch
    if num_epochs == 0:
        return None, 0  # 数据量不足一个epoch

    # 舍弃末尾不足一个epoch的数据
    df_trimmed = df.iloc[:num_epochs * samples_per_epoch].copy()

    # 创建epoch_id列，标记每个点属于哪个epoch
    df_trimmed['epoch_id'] = np.repeat(np.arange(num_epochs), samples_per_epoch)

    return df_trimmed, num_epochs, samples_per_epoch


# --- 保存每个epoch为单独文件 ---

def save_epochs_as_files(epoched_df, base_path, window_sec):
    """将每个epoch保存为单独的CSV文件"""
    # 创建保存epoch的目录
    epoch_dir = f"{base_path}_epochs_{window_sec}s"
    pathlib.Path(epoch_dir).mkdir(parents=True, exist_ok=True)

    # 获取所有唯一的epoch_id
    epoch_ids = epoched_df['epoch_id'].unique()

    # 为每个epoch创建单独的文件
    for epoch_id in epoch_ids:
        # 筛选当前epoch的数据
        epoch_data = epoched_df[epoched_df['epoch_id'] == epoch_id].copy()
        # 移除epoch_id列（可选，根据需要决定）
        epoch_data = epoch_data.drop(columns=['epoch_id'])
        # 构建输出文件名
        output_filename = f"{base_path}_epoch_{epoch_id:04d}.csv"
        output_path = os.path.join(epoch_dir, output_filename)
        # 保存文件
        epoch_data.to_csv(output_path, index=False)
    return epoch_dir


# ---Main---

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='将EEG数据切割成指定时长的epochs，并每个epoch保存为单独文件')
    parser.add_argument('--files', nargs='+', help='需要处理的CSV文件路径列表',default=["Processed_EEG_DEL_processed_remove.csv"])
    parser.add_argument('-w', '--window', type=float, default=1.0,help='每个epoch的时间长度(秒)，默认值为1.0秒')
    parser.add_argument('-v', '--verbose', action='store_true',help='显示详细处理信息')
    # 解析命令行参数
    args = parser.parse_args()
    print("开始进行数据分段...")
    print(f"使用的窗口时间长度: {args.window}秒")
    print(f"每个epoch将保存为单独的文件")
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"\n警告: 文件 '{file_path}' 不存在，已跳过。")
            continue
        print(f"\n正在处理: {file_path}")
        try:
            # 读取CSV文件
            df = pd.read_csv(file_path)
            # 从时间列重新计算采样率
            fs = 1 / np.mean(np.diff(df['time_diff']))
            if args.verbose:
                print(f"计算采样率: {fs:.2f} Hz")
            # 分段
            epoched_df, num_epochs, samples_per_epoch = create_epochs(
                df, fs, window_sec=args.window)
            if num_epochs == 0:
                print(f"警告: 文件 '{file_path}' 数据量不足，无法创建任何epoch")
                continue
            # 获取文件名（不含扩展名）
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            # 保存每个epoch为单独文件
            epoch_dir = save_epochs_as_files(epoched_df, base_name, args.window)
            print(f"分段完成，{num_epochs}个epochs已保存至→{epoch_dir}")
            if args.verbose:
                print(f"每个epoch包含{samples_per_epoch}个样本点")
        except Exception as e:
            print(f"处理文件 '{file_path}' 时出错: {str(e)}")
    print("\n所有文件处理完成")


if __name__ == "__main__":
    main()
