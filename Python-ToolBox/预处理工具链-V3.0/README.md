# XMuse EEG Preprocess Toolkit

轻量整合版工具包，用来把原来的三个功能目录串烧：
- `01_data_convert`: EDF/CSV/MAT 等格式转换
- `02_data_preprocess`: EEG 清洗、基线校正、滤波、极值修复、标准化、epoch分段
- `03_datadepart`: Muse Direct 导出的混合CSV按`PacketType`拆分整理

此版本优化重点：
1. 增加统一配置文件`config.json`，减少每个脚本里反复手改文件名和参数。
2. 增加预处理质量检查表，自动输出每个通道的缺失值、均值、标准差、最大最小值、采样率等信息。

## 目录说明
```text
xmuse_preprocess_tool/
  config.json              # 统一配置
  xmuse_toolkit.py          # 整合入口脚本
  README.md                 # 使用说明
  01_data_convert/          # 格式转换脚本
  02_data_preprocess/       # 预处理脚本
  03_datadepart/            # Direct数据整理脚本
  data/
    01/                     # EDF 示例数据
    02/                     # EEG CSV 示例数据
    03/                     # Muse Direct CSV 示例数据
  output/                   # 新脚本运行后自动生成
```

## 安装依赖
先进入工具包目录：
```bash
cd .../xmuse_preprocess_tool (用户自定义补全)
```

基础预处理需要：
```bash
pip install -r requirements.txt
```
其中 `scipy`用于滤波和MAT转换，`mne`用于EDF转CSV，如果暂时没有安装`scipy`，脚本会跳过滤波步骤并继续生成测试结果；正式处理数据时建议安装完整依赖。

## 配置文件
 `config.json`：
- `paths.preprocess_input_dir`: 原始EEG CSV输入目录，默认 `data/02`
- `paths.direct_input_dir`: Muse Direct CSV 输入目录，默认 `data/03`
- `paths.convert_input_dir`: EDF输入目录，默认 `data/01`
- `paths.output_dir`: 输出目录，默认 `output`
- `preprocess.files`: 要预处理的CSV文件名
- `preprocess.channels`: EEG通道名
- `preprocess.baseline_window_sec`: 基线校正时间窗
- `preprocess.highpass_hz` / `lowpass_hz` / `notch_hz`: 滤波参数
- `preprocess.amplitude_threshold`: 极值修复阈值
- `preprocess.scale_method`: `zscore` 或 `minmax`
- `preprocess.epoch.window_sec`: epoch窗口长度
- `preprocess.epoch.overlap_rate`: epoch重叠率，范围是 `0 <= overlap_rate < 1`

## 运行方法
只跑预处理：
```bash
python xmuse_toolkit.py preprocess
```

只跑Direct数据拆分：
```bash
python xmuse_toolkit.py direct
```

只跑格式转换：
```bash
python xmuse_toolkit.py convert
```

全部运行：
```bash
python xmuse_toolkit.py all
```

## 输出结果
预处理结果会输出到：
```text
output/preprocess/
```

包括：
- `*_preprocessed.csv`: 完成清洗、基线校正、滤波、极值修复、标准化后的连续数据
- `*_preprocessed_epoched.csv`: 分段后的数据，新增 `epoch_id`
- `quality_summary/*_quality_summary.csv`: 每个通道的质量检查表

Direct 拆分结果输出到：
```text
output/direct_data/
```

格式转换结果会输出到：

```text
output/convert/
```