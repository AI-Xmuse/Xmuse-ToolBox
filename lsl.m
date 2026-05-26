function lsl()
%% LSL多流实时查看器/记录器 - 每次运行重新自动匹配
clear; close all; clc;

%% ==================== 用户可调参数 ====================
window_time = 2;                    % 滚动窗口时长（秒） - 全局统一
data_gain = 1;                      % 数据显示增益（作用于去均值后的数据）
buffer_size = 20000;                % 每条流的数据缓冲区大小
max_mean_points = 5000;             % 用于均值计算的最近点数
print_interval = 100;               % 每100个样本打印一次时间信息
MANUAL_TIME_SCALE = 1e-6;           % 手动时间戳转换因子（微秒→秒）

% ===== 预定义的信号名称和对应的Y轴范围（共27个） =====
signal_names = {'JawClench', 'Accel', 'ThetaAbs', 'GammaScore', 'BetaScore', 'EEG', ...
                'Optics', 'ThetaRel', 'BetaAbs', 'AlphaAbs', 'IsGood', 'DeltaRel', ...
                'GammaRel', 'Gyro', 'HeadOn', 'HsiPrec', 'Batt', 'AlphaRel', ...
                'Blink', 'DeltaScore', 'PPG', 'GammaAbs', 'DeltaAbs', 'Therm', ...
                'ThetaScore', 'AlphaScore', 'BetaRel'};

signal_ylim = {[-2, 2], [-5, 5], [-2.5, 2.5], [-2.5, 2.5], [-2.5, 2.5], [-1500, 1500], ...
               [-1, 1], [-1, 1], [-2, 2], [-2, 2], [-5, 5], [-2, 2], ...
               [-1, 1], [-300, 300], [-1, 1], [-1, 1], [-2, 2], [-2, 2], ...
               [-1, 1], [-3, 3], [-10, 10], [-3, 3], [-3, 3], [-10, 10], ...
               [-3, 3], [-3, 3], [-2, 2]};

assert(length(signal_names) == length(signal_ylim), '信号名称与Y轴范围数量不匹配');

%% ==================== 初始化LSL ====================
lib = lsl_loadlib();
fprintf('LSL库加载成功。\n');

fprintf('扫描LSL流（超时5秒）...\n');
streams = lsl_resolve_all(lib, 5);
if isempty(streams)
    error('未发现任何LSL流。');
end

% 存储所有流信息
stream_info = struct('index', {}, 'name', {}, 'type', {}, 'channel_count', {}, ...
                     'nominal_srate', {}, 'inlet', {});
fprintf('发现 %d 个LSL流：\n', length(streams));
for i = 1:length(streams)
    stream_info(i).index = i;
    stream_info(i).name = streams{i}.name();
    stream_info(i).type = streams{i}.type();
    stream_info(i).channel_count = streams{i}.channel_count();
    stream_info(i).nominal_srate = streams{i}.nominal_srate();
    stream_info(i).inlet = lsl_inlet(streams{i});
    fprintf('  [%d] %s (类型: %s, 通道数: %d, 采样率: %.2f Hz)\n', ...
        i, stream_info(i).name, stream_info(i).type, ...
        stream_info(i).channel_count, stream_info(i).nominal_srate);
end

%% ==================== 根据类型自动匹配信号 ====================
fprintf('\n尝试根据流类型自动匹配信号...\n');
auto_matched = true;
selected_signal_names = cell(length(stream_info), 1);

for i = 1:length(stream_info)
    matched_idx = [];
    for j = 1:length(signal_names)
        if strcmpi(stream_info(i).type, signal_names{j})
            matched_idx = j;
            break;
        end
    end
    if ~isempty(matched_idx)
        selected_signal_names{i} = signal_names{matched_idx};
        fprintf('  流 %d (%s) 类型 %s 匹配信号: %s\n', i, stream_info(i).name, stream_info(i).type, signal_names{matched_idx});
    else
        auto_matched = false;
        fprintf('  流 %d (%s) 类型 %s 无法匹配任何信号\n', i, stream_info(i).name, stream_info(i).type);
    end
end

% 如果没有完全匹配成功，则弹出手动映射界面
if ~auto_matched
    fprintf('\n部分流无法自动匹配，将打开手动映射界面。\n');
    
    fig_sel = uifigure('Name', '选择信号映射', 'Position', [100,100,900,650]);
    
    colNames = {'流序号', '流名称', '类型', '通道数', '选择信号'};
    data = cell(length(stream_info), 5);
    for i = 1:length(stream_info)
        data{i,1} = i;
        data{i,2} = stream_info(i).name;
        data{i,3} = stream_info(i).type;
        data{i,4} = stream_info(i).channel_count;
        data{i,5} = signal_names{1};
    end
    tbl = uitable(fig_sel, 'Data', data, 'ColumnName', colNames, ...
        'ColumnEditable', [false, false, false, false, true], ...
        'ColumnFormat', {[], [], [], [], signal_names}, ...
        'Position', [20, 100, 860, 480]);

    btn_auto = uibutton(fig_sel, 'push', 'Text', '自动按顺序匹配', ...
        'Position', [300, 50, 150, 30], ...
        'ButtonPushedFcn', @(btn,event) autoMatch(tbl));
    btn_ok = uibutton(fig_sel, 'push', 'Text', '确认', 'Position', [470, 50, 100, 30], ...
        'ButtonPushedFcn', @(btn,event) uiresume(fig_sel));
    btn_cancel = uibutton(fig_sel, 'push', 'Text', '取消', 'Position', [590, 50, 100, 30], ...
        'ButtonPushedFcn', @(btn,event) cancelCallback(fig_sel));

    uiwait(fig_sel);
    if ~isvalid(fig_sel)
        for i = 1:length(stream_info)
            if ~isempty(stream_info(i).inlet)
                delete(stream_info(i).inlet);
            end
        end
        delete(lib);
        fprintf('用户取消操作，程序退出。\n');
        return;
    end
    selected_signal_cells = tbl.Data(:,5);
    close(fig_sel);
    for i = 1:length(stream_info)
        selected_signal_names{i} = selected_signal_cells{i};
    end
else
    fprintf('\n所有流已根据类型自动匹配成功。\n');
end

%% ==================== 根据选择设置每个流的matched_signal和ylim_fixed ====================
for i = 1:length(stream_info)
    selected_name = selected_signal_names{i};
    idx = find(strcmp(signal_names, selected_name), 1);
    if isempty(idx)
        warning('流 %d 选择的信号 "%s" 不在预定义列表中，将使用自动缩放。', i, selected_name);
        stream_info(i).matched_signal = '未知';
        stream_info(i).ylim_fixed = [];
    else
        stream_info(i).matched_signal = signal_names{idx};
        stream_info(i).ylim_fixed = signal_ylim{idx};
        fprintf('流 %d (%s) 已匹配信号: %s, Y轴范围 [%.2f, %.2f]\n', ...
            i, stream_info(i).name, signal_names{idx}, ...
            signal_ylim{idx}(1), signal_ylim{idx}(2));
    end
end

%% ==================== 创建图形界面 ====================
fig = figure('Name', 'LSL多流查看器', 'Position', [100,100,1200,800], ...
             'NumberTitle', 'off', 'CloseRequestFcn', @closeFigure);

% 控制面板（下拉菜单保留在左上角）
uicontrol('Style', 'text', 'String', '选择流:', 'Position', [20, 750, 60, 25]);
stream_menu = uicontrol('Style', 'popupmenu', 'Position', [80, 750, 300, 25], ...
                       'Callback', @changeStream);
menu_strings = arrayfun(@(i) sprintf('[%d] %s (%s, %d ch) - %s', i, ...
    stream_info(i).name, stream_info(i).type, stream_info(i).channel_count, ...
    stream_info(i).matched_signal), 1:length(stream_info), 'UniformOutput', false);
set(stream_menu, 'String', menu_strings, 'Value', 1);

% 记录/停止按钮 + 计时显示（移至波形区域右上角）
record_btn = uicontrol('Style', 'pushbutton', 'String', '开始记录', ...
                      'Position', [900, 750, 100, 30], 'Callback', @startRecording);
stop_btn = uicontrol('Style', 'pushbutton', 'String', '停止记录', ...
                    'Position', [1010, 750, 100, 30], 'Callback', @stopRecording, ...
                    'Enable', 'off');
% 计时标签：增加宽度至 180，确保显示完整
timer_text = uicontrol('Style', 'text', 'String', '记录时长: 00:00', ...
                       'Position', [720, 750, 180, 25], 'HorizontalAlignment', 'left');

% 初始化数据存储结构
for i = 1:length(stream_info)
    stream_info(i).time_offset = 0;
    stream_info(i).sample_count = 0;
    stream_info(i).raw_buffer = zeros(max_mean_points, stream_info(i).channel_count);
    stream_info(i).raw_ptr = 1;
    stream_info(i).raw_full = false;
    stream_info(i).ax = [];
    stream_info(i).lines = [];
    stream_info(i).time_scale = MANUAL_TIME_SCALE;   % 使用手动缩放因子
    stream_info(i).first_ts = [];
    stream_info(i).second_ts = [];
end

% 当前选中的流索引
current_idx = 1;
is_recording = false;
record_fileID = -1;
record_start_time = 0;      % 用于计时（tic）
last_timer_update = 0;      % 上次更新时间（秒）

% 创建第一个流的子图
createStreamPlots(current_idx);

fprintf('\n开始实时接收... (关闭窗口停止)\n');
fprintf('窗口时长: %d 秒（全局统一），增益: %d\n', window_time, data_gain);
fprintf('手动时间缩放因子已启用: %g (微秒→秒)\n', MANUAL_TIME_SCALE);
fprintf('每 %d 个样本打印一次时间信息。\n\n', print_interval);

%% ==================== 实时循环 ====================
while ishandle(fig)
    idx = current_idx;
    inlet = stream_info(idx).inlet;
    n_chans = stream_info(idx).channel_count;
    
    [data, ts] = inlet.pull_sample(0);
    if ~isempty(data)
        stream_info(idx).sample_count = stream_info(idx).sample_count + 1;
        
        % 手动时间戳处理：首次采样时设置时间偏移
        if stream_info(idx).sample_count == 1
            stream_info(idx).time_offset = ts;
            fprintf('流 %d: 使用手动时间缩放因子: %g\n', idx, MANUAL_TIME_SCALE);
        end
        
        % 数据长度处理
        if length(data) > n_chans
            data = data(1:n_chans);
        elseif length(data) < n_chans
            data = [data; zeros(n_chans-length(data),1)];
        end
        data(isnan(data)) = 0;
        
        % 计算相对时间（秒）
        rel_t = (ts - stream_info(idx).time_offset) * stream_info(idx).time_scale;
        
        % 更新原始数据缓冲区
        buf = stream_info(idx).raw_buffer;
        ptr = stream_info(idx).raw_ptr;
        buf(ptr,:) = data';
        stream_info(idx).raw_buffer = buf;
        stream_info(idx).raw_ptr = mod(ptr, max_mean_points) + 1;
        if ptr == max_mean_points
            stream_info(idx).raw_full = true;
        end
        
        % 计算各通道均值（排除零值）
        if stream_info(idx).raw_full
            buf_use = stream_info(idx).raw_buffer;
        else
            buf_use = stream_info(idx).raw_buffer(1:ptr,:);
        end
        mean_vals = zeros(1, n_chans);
        for ch = 1:n_chans
            non_zero = buf_use(:, ch);
            non_zero = non_zero(non_zero ~= 0);
            if ~isempty(non_zero)
                mean_vals(ch) = mean(non_zero);
            end
        end
        
        cur_point = (data - mean_vals) * data_gain;
        
        ax = stream_info(idx).ax;
        lines = stream_info(idx).lines;
        
        for ch = 1:n_chans
            addpoints(lines(ch), rel_t, cur_point(ch));
        end
        
        % 更新X轴范围
        x_min = max(0, rel_t - window_time);
        x_max = rel_t;
        if x_min < x_max
            for ch = 1:n_chans
                set(ax(ch), 'XLim', [x_min, x_max]);
            end
        end
        
        % Y轴设置：如果该流有固定范围，则使用固定值；否则自动缩放
        if ~isempty(stream_info(idx).ylim_fixed)
            for ch = 1:n_chans
                ylim(ax(ch), stream_info(idx).ylim_fixed);
            end
        else
            for ch = 1:n_chans
                [y, ~] = getpoints(lines(ch));
                if ~isempty(y)
                    valid = y(y ~= 0);
                    if ~isempty(valid)
                        y_min = min(valid);
                        y_max = max(valid);
                        if y_max == y_min
                            y_lo = y_min - 0.001;
                            y_hi = y_max + 0.001;
                        else
                            y_lo = y_min;
                            y_hi = y_max;
                        end
                        ylim(ax(ch), [y_lo, y_hi]);
                    else
                        ylim(ax(ch), [-0.001, 0.001]);
                    end
                end
            end
        end
        
        % 记录数据（保存为秒级时间戳，保留6位小数，无科学计数法）
        if is_recording && idx == current_idx
            timestamp_sec = ts * stream_info(idx).time_scale;
            fprintf(record_fileID, '%15.6f', timestamp_sec);
            for ch = 1:n_chans
                fprintf(record_fileID, ',%.6f', data(ch));
            end
            fprintf(record_fileID, '\n');
        end
        
        % 调试打印
        if mod(stream_info(idx).sample_count, print_interval) == 1
            fprintf('流 %d (%s) 样本 %d: 当前时间 = %.2f s, 窗口 [%.2f, %.2f]\n', ...
                idx, stream_info(idx).matched_signal, stream_info(idx).sample_count, rel_t, x_min, x_max);
        end
        
        drawnow limitrate;
    else
        pause(0.0005);
    end
    
    % 更新计时显示（格式：分:秒，超过1小时自动切换为时:分:秒）
    if is_recording
        current_time = toc(record_start_time);
        if current_time - last_timer_update >= 0.1
            if current_time >= 3600
                hours = floor(current_time / 3600);
                minutes = floor(mod(current_time, 3600) / 60);
                seconds = mod(current_time, 60);
                set(timer_text, 'String', sprintf('记录时长: %02d:%02d:%02d', hours, minutes, seconds));
            else
                minutes = floor(current_time / 60);
                seconds = mod(current_time, 60);
                set(timer_text, 'String', sprintf('记录时长: %02d:%02d', minutes, seconds));
            end
            last_timer_update = current_time;
        end
    end
end

%% ==================== 清理 ====================
    function closeFigure(~, ~)
        if is_recording
            stopRecording();
        end
        for i = 1:length(stream_info)
            if ~isempty(stream_info(i).inlet)
                delete(stream_info(i).inlet);
            end
        end
        delete(fig);
    end

%% ==================== 创建子图（用于指定流）====================
    function createStreamPlots(stream_idx)
        if ~isempty(stream_info(stream_idx).ax) && all(isgraphics(stream_info(stream_idx).ax))
            delete(stream_info(stream_idx).ax);
        end
        
        n_chans = stream_info(stream_idx).channel_count;
        ax = gobjects(n_chans,1);
        lines = gobjects(n_chans,1);
        colors = jet(n_chans);
        
        stream_type = stream_info(stream_idx).type;
        matched_signal = stream_info(stream_idx).matched_signal;
        ylim_fixed = stream_info(stream_idx).ylim_fixed;
        
        for ch = 1:n_chans
            [axis_name, type_display] = getAxisTitle(stream_type, ch, n_chans);
            ax(ch) = subplot(n_chans,1,ch, 'Parent', fig);
            title(ax(ch), sprintf('%s (%s) %s', type_display, matched_signal, axis_name));
            if isempty(ylim_fixed)
                ylabel(ax(ch), '幅值 (自动缩放)');
            else
                ylabel(ax(ch), sprintf('幅值 [%.2f, %.2f]', ylim_fixed(1), ylim_fixed(2)));
            end
            grid(ax(ch), 'on');
            hold(ax(ch), 'on');
            xlim(ax(ch), [0 window_time]);
            lines(ch) = animatedline(ax(ch), 'Color', colors(ch,:), ...
                                      'LineWidth', 1, 'MaximumNumPoints', buffer_size);
        end
        xlabel(ax(end), '时间 (s)');
        
        stream_info(stream_idx).ax = ax;
        stream_info(stream_idx).lines = lines;
    end

%% ==================== 辅助函数：获取轴标题 ====================
    function [axis_name, type_display] = getAxisTitle(stream_type, ch_idx, n_chans)
        type_lower = lower(stream_type);
        if contains(type_lower, 'acc')
            type_display = '陀螺仪';
        elseif contains(type_lower, 'gyro')
            type_display = '加速度';
        else
            type_display = upper(stream_type);
        end
        if n_chans == 3 && (contains(type_lower, 'acc') || contains(type_lower, 'gyro'))
            switch ch_idx
                case 1, axis_name = 'X轴';
                case 2, axis_name = 'Y轴';
                case 3, axis_name = 'Z轴';
                otherwise, axis_name = sprintf('通道%d', ch_idx);
            end
        else
            axis_name = sprintf('通道%d', ch_idx);
        end
    end

%% ==================== 辅助函数：获取通道名称（用于CSV表头）====================
    function chan_names = getChannelNames(stream_type, n_chans)
        type_lower = lower(stream_type);
        if contains(type_lower, 'acc')
            prefix = 'Gyro';
        elseif contains(type_lower, 'gyro')
            prefix = 'Acc';
        else
            prefix = upper(stream_type);
        end
        chan_names = cell(1, n_chans);
        if n_chans == 3 && (contains(type_lower, 'acc') || contains(type_lower, 'gyro'))
            axes = {'X', 'Y', 'Z'};
            for ch = 1:n_chans
                chan_names{ch} = sprintf('%s_%s', prefix, axes{ch});
            end
        else
            for ch = 1:n_chans
                chan_names{ch} = sprintf('%s_Ch%d', prefix, ch);
            end
        end
    end

%% ==================== 切换流回调 ====================
    function changeStream(~, ~)
        new_idx = get(stream_menu, 'Value');
        if new_idx ~= current_idx
            if is_recording
                warndlg('请先停止记录再切换流', '记录进行中');
                set(stream_menu, 'Value', current_idx);
                return;
            end
            current_idx = new_idx;
            delete(findall(fig, 'Type', 'axes'));
            createStreamPlots(current_idx);
        end
    end

%% ==================== 开始记录 ====================
    function startRecording(~, ~)
        if is_recording, return; end
        idx = current_idx;
        
        dir_name = uigetdir(pwd, '选择保存目录');
        if dir_name == 0, return; end
        
        safe_name = regexprep(stream_info(idx).name, '[^a-zA-Z0-9_]', '_');
        default_name = sprintf('LSL_%s_%s.csv', safe_name, datestr(now, 'yyyymmdd_HHMMSS'));
        
        answer = inputdlg('请输入文件名（扩展名自动添加.csv）:', '保存数据', [1 50], {default_name});
        if isempty(answer), return; end
        filename = answer{1};
        
        [~,~,ext] = fileparts(filename);
        if isempty(ext)
            filename = [filename, '.csv'];
        elseif ~strcmpi(ext, '.csv')
            filename = [filename, '.csv'];
        end
        
        fullpath = fullfile(dir_name, filename);
        
        fileID = fopen(fullpath, 'w');
        if fileID == -1
            errordlg(sprintf('无法创建文件：%s\n请检查路径权限。', fullpath), '文件错误');
            return;
        end
        fprintf(fileID, 'Timestamp');
        chan_names = getChannelNames(stream_info(idx).type, stream_info(idx).channel_count);
        for ch = 1:stream_info(idx).channel_count
            fprintf(fileID, ',%s', chan_names{ch});
        end
        fprintf(fileID, '\n');
        
        is_recording = true;
        record_fileID = fileID;
        record_start_time = tic;
        last_timer_update = 0;
        set(timer_text, 'String', '记录时长: 00:00');
        set(record_btn, 'Enable', 'off');
        set(stop_btn, 'Enable', 'on');
        set(stream_menu, 'Enable', 'off');
        fprintf('开始记录数据到文件: %s\n', fullpath);
    end

%% ==================== 停止记录 ====================
    function stopRecording(~, ~)
        if ~is_recording, return; end
        if record_fileID ~= -1
            fclose(record_fileID);
            record_fileID = -1;
        end
        is_recording = false;
        set(record_btn, 'Enable', 'on');
        set(stop_btn, 'Enable', 'off');
        set(stream_menu, 'Enable', 'on');
        set(timer_text, 'String', '记录时长: 00:00');
        fprintf('记录已停止。\n');
    end

%% ==================== 手动映射界面回调函数 ====================
    function autoMatch(tbl)
        newData = tbl.Data;
        numStreams = size(newData,1);
        for i = 1:numStreams
            idx = mod(i-1, length(signal_names)) + 1;
            newData{i,5} = signal_names{idx};
        end
        tbl.Data = newData;
    end

    function cancelCallback(fig_sel)
        close(fig_sel);
    end

end