# -*-coding: Utf-8 -*-
# @File : data_interpolation.py
# author: Gion Hua
# Time：2025/9/4

import pandas as pd
import numpy as np
import os
import argparse
from typing import Tuple


def interpolate_outliers(df: pd.DataFrame, threshold: float, channels: list) -> Tuple[pd.DataFrame, int]:
    """
    功能: 在给定的表中检测并插值超过阈值的点
    """
    total_interpolated_count = 0

    for chan in channels:
        if chan not in df.columns:
            print(f"警告: 通道'{chan}'不在数据列中，跳过处理")
            continue
        signal = df[chan].copy()  # 使用copy避免SettingWithCopyWarning
        # 找到绝对值超过阈值的坏点
        bad_indices = np.abs(signal) > threshold
        bad_points_count = bad_indices.sum()

        if bad_points_count > 0:
            print(f"{chan}找到{bad_points_count}个极值点插值...")
            total_interpolated_count += bad_points_count

            # 坏点设为NaN，线性插值填充
            signal[bad_indices] = np.nan
            df[chan] = signal.interpolate(method='linear', limit_direction='both')
        else:
            print(f"{chan}无坏点")

    return df, total_interpolated_count


def main():
    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(description='EEG数据异常值检测与插值处理')

    # 文件路径（可指定多个）
    parser.add_argument('--files', nargs='+', help='需要处理的CSV文件路径，多个文件用空格分隔',default=["Processed_EEG_DEL_processed.csv"])
    # 可选参数
    parser.add_argument('--threshold', type=float, default=100,help='振幅阈值(µV)，超过此值的点将被插值，默认: 100')
    parser.add_argument('--channels', nargs='+', default=["TP9", "AF7", "AF8", "TP10"],help=f'需要处理的EEG通道列表，默认: TP9 AF7 AF8 TP10')
    parser.add_argument('--output-suffix', default='_remove',help='处理后文件的名称后缀，默认: _remove')
    parser.add_argument('--overwrite', action='store_true',help='如果输出文件已存在，是否覆盖（默认不覆盖）')

    # 解析参数
    args = parser.parse_args()

    # 显示参数信息
    print("===== 处理参数 =====")
    print(f"处理文件: {args.files}")
    print(f"振幅阈值: {args.threshold} µV")
    print(f"处理通道: {args.channels}")
    print(f"输出文件后缀: {args.output_suffix}")
    print(f"是否覆盖已存在文件: {'是' if args.overwrite else '否'}")
    print("===================\n")

    # 处理每个文件
    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"\n⚠️ 文件'{file_path}'不存在，跳过处理")
            continue

        print(f"\n正在处理: {file_path}")

        # 读取CSV文件
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}，跳过该文件")
            continue

        # 执行插值处理
        df_interpolated, num_fixed = interpolate_outliers(df, args.threshold, args.channels)

        # 有修改且需要保存时处理
        if num_fixed > 0:
            # 构建输出文件路径
            base, ext = os.path.splitext(file_path)
            output_path = f"{base}{args.output_suffix}{ext}"

            # 检查文件是否已存在
            if os.path.exists(output_path) and not args.overwrite:
                print(f"⚠️ 输出文件 '{output_path}' 已存在，未覆盖（使用--overwrite参数可强制覆盖）")
                continue

            # 保存文件
            try:
                df_interpolated.to_csv(output_path, index=False)
                print(f"✅ 已保存至→'{output_path}'")
            except Exception as e:
                print(f"❌ 保存文件失败: {e}")
        else:
            print("ℹ️ 未发现需要插值的点，不生成新文件")

    print("\n所有文件处理完成")


if __name__ == "__main__":
    main()
