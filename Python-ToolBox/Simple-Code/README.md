# 脑电信号处理代码工具箱

## 💕项目简介

⚒️⚒️这是一个用于处理和分析Xmuse Lab/PYLSL保存的脑电信号(EEG)数据工具集，提供了数据预处理、数据格式转换、时间戳转换、数据滤波、脑电功率谱密度分析等功能，主要帮助脑接口领域的科研人员更快上手便携式脑电波仪Xmuse并进行相关的数据处理的开发工作。

## 💕主要功能

### 01. 时间戳转换

- **支持把Xmuse Lab/PYLSL保存的数据进行时间戳的计算，将其时间戳timesstamp转换为北京时间。**

- 使用说明：

  （1）将下面的文件地址替换为你的脑电数据csv格式的地址

  ```python
  input_csv = "EEG_signal.csv"  # 替换为您的原始 CSV 文件路径
  ```

  （2）判断自己脑电数据是通过Xmuse Lab采集的，还是通过PYLSL采集的，并根据对应代码格式选择使用对应的代码。

  ```python
  "如果是通过PYLSL保存的数据格式，把下面注释的代码取消注释"
  #timestamp = timestamp / 1000000.0    # 将微秒转换为秒（除以1,000,000）
  "转换为北京时间（针对Xmuse Lab保存的数据格式）"
  beijing_time = datetime.datetime.utcfromtimestamp(timestamp) + datetime.timedelta(hours=8)
  ```

### 02. 数据转换

- **支持把Xmuse Lab保存的EDF格式的脑电数据转换为CSV格式的。**

- 使用说明：

  （1）将下面文件地址替换为你的脑电数据edf格式的地址

  ```
  edf_file = 'xmuselab_recording(45).edf'
  ```

  （2）将下面文件地址替换为你的脑电数据edf格式转换为CSV的地址

  ```
  csv_file = '1100.csv'
  ```

### 03. 数据预处理

- **支持把Xmuse Lab保存的脑电的CSV文件进行数据清洗（去除缺失值和含有0的行），并进行时间戳之间的差值。**

- 使用说明：

  （1）将下面的文件地址替换为你的脑电数据csv格式的地址

  ```python
  if __name__ == '__main__':
      #放入你脑电文件的地址
      analyze_eeg_data("xmuselab_recording(45).csv")
  ```

### 04. 数据滤波

- **支持对4通道脑电数据进行高通滤波、低通滤波、带通滤波、陷波滤波等一系列操作，并在时域上可视化对比滤波前后脑电数据。**

- 使用说明：

  （1）将下面文件的地址改成自己文件的地址，🔊**特别注意这里导入的数据格式是经过预处理的：只有时间戳和4通道的EEG数据。**

  ```
  if __name__ == '__main__':
      #这里导入的数据格式是经过预处理的，只有时间戳和4通道的EEG数据
      main(csv_filename='EEG_signal.csv')
  ```

### 05. 脑电功率谱密度计算

- **支持对脑电数据进行频段能量分析（五个频段的绝对功率和相对功率百分比计算）、频谱熵计算、Hjorth参数分析、频谱图可视化。**

- 使用说明：

  （1）将下面的地址改成自己脑电数据的地址，🔊**特别注意这里导入的数据格式是经过预处理的：只有时间戳和4通道的EEG数据。**

  ```
  if __name__ == '__main__':
      "脑电数据的地址"
      data_path = "EEG_signal.csv"
  ```


### 06. 基线校正

- **目前我们通过这个Xmuse Lab采集到的脑电数据的电压都是在800uv左右的，正常我们大脑头皮外层的电压是在100uv前后的，所以我们需要对数据进行预处理，让整个数据都在基准上下波动，且波动的范围在100uv前后，一种方法是直接减去一个固定的偏移值800（因为硬件本身具有固定的偏置）,另一种方法是减去每个通道的平均值（数据采集时的）。**

- 使用说明：根据这个解析器的参数来选择自己的需要处理的csv脑电数据和需要使用的方法（可通过阅读help里面的内容实现参数的改变）。

```python
def main():
    parser = argparse.ArgumentParser(description='EEG数据处理：列名替换与基线校正')
    # 文件路径（可指定多个）
    parser.add_argument('--files', nargs='+', help='需要处理的CSV文件路径',default=['Processed_EEG_DEL.csv','processed_eeg_data.csv'])
    parser.add_argument('--baseline-method', type=int, default=2, choices=[1, 2],help='基线校正方法 (1: DC校正, 2: 通道独立基线校正，默认: 2)')
    parser.add_argument('--baseline-start', type=float, default=0.0,help='基线期起始时间(秒)，默认: 0.0')
    parser.add_argument('--baseline-end', type=float, default=0.2,help='基线期结束时间(秒)，默认: 0.2')
    parser.add_argument('--dc-offset', type=int, default=800,help='DC校正的偏移值，默认: 800')
    parser.add_argument('--channels', nargs='+', default=['TP9', 'AF7', 'AF8', 'TP10'],help=f'需要处理的通道列表，默认: TP9 AF7 AF8 TP10')
    # 解析参数
```



### 07. 数据插值

- **这个插值的过程是跟数据滤波相关联的，因为我们再处理滤波之后还会存在一些极值点，我们将使用插值算法来计算这个值并进行替代**

- 使用说明：根据这个解析器的参数来选择自己的需要处理的csv脑电数据（默认将这个超过100uv的数值判断为极值）。

```python
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

```



### 08. 数据预处理（归一化和标准化）

- **在机器学习和深度学习里面，数据预处理中的数据标准化是重要的一个步骤，根据实际场景需要进行使用，如果对输出结果范围有要求，用归一化；如果数据存在异常值和较多噪音，用标准化，可以间接通过中心化避免异常值和极端值的影响**

- 使用说明：可以选择使用归一化的预处理，也可以选择使用标准化的预处理，看实际数据预处理的需求吧。

```python
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
```



### 09. 数据切片（Epoch）

- **在使用脑电数据进行模型的训练的时候，数据的切片是必不可少的，不管是监督学习还是无监督学习，数据切片操作可以让模型更好的从时序序列的数据中提取这个特征。**

- 使用说明：可以在这个window里面修改自己想要对数据进行切片的时间窗口参数，根据自己的需求和模型的部署情况。

```python

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='将EEG数据切割成指定时长的epochs，并每个epoch保存为单独文件')
    parser.add_argument('--files', nargs='+', help='需要处理的CSV文件路径列表',default=["Processed_EEG_DEL_processed_remove.csv"])
    parser.add_argument('-w', '--window', type=float, default=1.0,help='每个epoch的时间长度(秒)，默认值为1.0秒')
    parser.add_argument('-v', '--verbose', action='store_true',help='显示详细处理信息')
```



## 💕环境要求

- Python 3.6+
- 依赖包：numpy、pandas、scipy、matplotlib、mne

## 💕注意事项

- 使用前请确保先阅读README文档并进行对应的库的安装。
- 使用前确保自己的数据格式与代码中的数据格式一致。
- 注意检查采样率设置是否正确，Xmuse便携式脑电波仪的采样率为256Hz。

## 💕联系方式

- 作者：【漂泊的小森-Gion】
- 邮箱：[huags@xmuse.cn]

---


🗨️🗨️***如有问题或建议，欢迎提交 Issue 或通过邮件联系。***
