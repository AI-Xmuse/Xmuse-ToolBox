该系列脚本（MuseDirect_csv_process）负责将MuseDirect采集的csv数据进行拆分，并将EEG与记录的事件时间戳进行对齐，导入mne。

0_timestamp_recorder.py

该脚本负责辅助进行事件标签的记录。修改脚本中
buttons = ['EC','EO','Blink', 'Jaw', 'Frown','sacc','nod','talk','updown','empty']
为想要的任务标签，使用python运行即可。注意，请记得结束时点击保存记录。

1_museDirectcsv_splitmodalities.py

该脚本负责将museDirect采集的csv数据拆分为不同的模态。修改脚本中
split_by_packettype(rf'D:\Projects\Data&Labels\TestData\2025-08-12-14-15-59.csv')
为museDirect采集的csv文件位置即可。

2_annotation_alignment.py

该脚本负责将采集的EEG数据与记录的事件时间戳进行merge，并导入到mne中。比较特殊的是（如脚本中所示），我们建议使用样本数量/256的方式作为onset。

请注意，如果实验对于时间戳的同步要求极高（比如ERP的0.05s内），请在实验前联系Xmuse团队。
