import pandas as pd
import os
import argparse
from typing import Callable

def normalize_channel(data: pd.Series) -> pd.Series:
    """(Min-Max) 将数据归一化到 [0, 1] 区间
    Args:
        data: 输入的通道数据
    Returns:
        归一化后的通道数据
    """
    min_val = data.min()
    max_val = data.max()
    # 处理数据全部相同的特殊情况（避免除零错误）
    if max_val == min_val:
        return pd.Series(0, index=data.index)
    return (data - min_val) / (max_val - min_val)

def standardize_channel(data: pd.Series) -> pd.Series:
    """(Z-Score) 将数据标准化为均值0，标准差1
    Args:
        data: 输入的通道数据
    Returns:
        标准化后的通道数据
    """
    mean_val = data.mean()
    std_val = data.std()
    # 处理数据全部相同的特殊情况（避免除零错误）
    if std_val == 0:
        return pd.Series(0, index=data.index)
    return (data - mean_val) / std_val

def get_scale_function(method: str) -> Callable[[pd.Series], pd.Series]:
    """获取指定的缩放函数
    Args:
        method: 缩放方法名称 ('zscore' 或 'minmax')
    Returns:
        对应的缩放函数
    """
    method_mapping = {
        'zscore': standardize_channel,
        'minmax': normalize_channel
    }
    return method_mapping[method]
def process_file(file_path: str,
                 channels: list,
                 scale_func: Callable[[pd.Series], pd.Series],
                 output_suffix: str,
                 overwrite: bool) -> None:
    """处理单个文件的缩放逻辑
    Args:
        file_path: 输入文件路径
        channels: 需要处理的通道列表
        scale_func: 缩放函数
        output_suffix: 输出文件后缀
        overwrite: 是否覆盖已存在的文件
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"⚠️ 文件 '{file_path}' 不存在，跳过处理")
        return
    print(f"\n正在处理：{file_path}")
    # 读取CSV文件
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        print(f"❌ 读取文件失败：{str(e)}，跳过该文件")
        return
    # 处理每个通道
    processed_channels = 0
    missing_channels = []
    for chan in channels:
        if chan in df.columns:
            df[chan] = scale_func(df[chan])
            processed_channels += 1
        else:
            missing_channels.append(chan)
    # 反馈通道处理情况
    if processed_channels > 0:
        print(f"✅ 已成功缩放 {processed_channels} 个通道")
    if missing_channels:
        print(f"⚠️ 未找到 {len(missing_channels)} 个通道：{', '.join(missing_channels)}")
    # 没有处理任何通道时不生成输出文件
    if processed_channels == 0:
        print("ℹ️ 未处理任何通道，不生成输出文件")
        return
    # 构建输出路径
    base, ext = os.path.splitext(file_path)
    output_path = f"{base}{output_suffix}{ext}"
    # 处理文件覆盖逻辑
    if os.path.exists(output_path) and not overwrite:
        print(f"⚠️ 输出文件 '{output_path}' 已存在，未覆盖（使用--overwrite参数可强制覆盖）")
        return
    # 保存处理后的文件
    try:
        df.to_csv(output_path, index=False)
        print(f"✅ 处理完成，文件已保存至：{output_path}")
    except Exception as e:
        print(f"❌ 保存文件失败：{str(e)}")


def main():
    # 配置命令行参数解析器
    parser = argparse.ArgumentParser(description='EEG数据缩放工具')

    # 必选参数
    parser.add_argument('--files',nargs='+',help='需要处理的CSV文件路径（多个文件用空格分隔）',default=["Processed_EEG_DEL_processed_remove.csv"])
    # 可选参数
    parser.add_argument('--channels',nargs='+',default=['TP9', 'AF7', 'AF8','TP10'],help='需要缩放的EEG通道列表')
    parser.add_argument('--scale-method',type=str,choices=['zscore', 'minmax'], default='zscore',help='数据缩放方法')
    parser.add_argument('--output-suffix',help=f'输出文件后缀（默认：zscore→_std，minmax→_nml）')
    parser.add_argument('--overwrite',action='store_true',help='覆盖已存在的输出文件')
    # 解析参数
    args = parser.parse_args()
    # 确定输出后缀
    if not args.output_suffix:
        args.output_suffix = '_std' if args.scale_method == 'zscore' else '_nml'

    # 获取缩放函数
    scale_func = get_scale_function(args.scale_method)

    # 显示配置信息
    print("===== 处理配置 =====")
    print(f"处理文件数量：{len(args.files)}")
    print(f"目标通道：{', '.join(args.channels)}")
    print(f"缩放方法：{args.scale_method}")
    print(f"输出后缀：{args.output_suffix}")
    print(f"允许覆盖：{'是' if args.overwrite else '否'}")
    print("===================\n")

    # 批量处理文件
    for file_path in args.files:
        process_file(file_path=file_path,channels=args.channels,scale_func=scale_func,output_suffix=args.output_suffix,overwrite=args.overwrite)
    print("\n所有文件处理完毕")


if __name__ == "__main__":
    main()
