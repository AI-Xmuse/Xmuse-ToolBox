function osc()
%% OSC数据流自动发现与显示 - 重构绘图部分（使用 animatedline）
clear; close all; clc;

%% 参数设置
window_time = 2;          % 显示窗口时长 (秒)
DEBUG_MODE = true;          % 调试输出开关
MAX_POINTS_PER_LINE = 5000; % 每条曲线的最大点数（animatedline 内部环形缓冲区）

% ========== 用户输入 UDP 端口和本地地址 ==========
prompt = {'UDP 端口号 (1024-65535):', '本地IP地址 (留空表示所有接口):'};
dlgtitle = 'UDP 配置';
dims = [1 40];
definput = {'7000', ''};
answer = inputdlg(prompt, dlgtitle, dims, definput);
if isempty(answer)
    fprintf('用户取消输入，程序退出。\n');
    return;
end

udp_port_str = strtrim(answer{1});
local_host = strtrim(answer{2});

if isempty(udp_port_str)
    errordlg('端口号不能为空', '输入错误');
    return;
end
udp_port = str2double(udp_port_str);
if isnan(udp_port) || udp_port < 1 || udp_port > 65535 || mod(udp_port,1)~=0
    errordlg('端口号必须是 1-65535 之间的整数', '输入错误');
    return;
end

% ========== 预设信号名称与Y轴范围（27个） ==========
signal_names = {'JawClench', 'Accel', 'ThetaAbs', 'GammaScore', 'BetaScore', 'EEG', ...
                'Optics', 'ThetaRel', 'BetaAbs', 'AlphaAbs', 'IsGood', 'DeltaRel', ...
                'GammaRel', 'Gyro', 'HeadOn', 'HsiPrec', 'Batt', 'AlphaRel', ...
                'Blink', 'DeltaScore', 'PPG', 'GammaAbs', 'DeltaAbs', 'Therm', ...
                'ThetaScore', 'AlphaScore', 'BetaRel'};

signal_ylim = {[-2, 2], [-5, 5], [-2.5, 2.5], [-2.5, 2.5], [-2.5, 2.5], [-500, 1800], ...
               [-1, 1], [-1, 1], [-2, 2], [-2, 2], [-5, 5], [-2, 2], ...
               [-1, 1], [-300, 300], [-1, 1], [-1, 1], [-2, 2], [-2, 2], ...
               [-1, 1], [-3, 3], [-10, 10], [-3, 3], [-3, 3], [-10, 10], ...
               [-3, 3], [-3, 3], [-2, 2]};

preset_map = containers.Map();
for i = 1:length(signal_names)
    preset_map(lower(signal_names{i})) = signal_ylim{i};
end

% 变体映射
variant_map = containers.Map();
variant_map('eeg') = 'eeg';
variant_map('gyro') = 'gyro';
variant_map('acc') = 'accel';
variant_map('blink') = 'blink';
variant_map('jaw_clench') = 'jawclench';
variant_map('touching_forehead') = 'headon';
variant_map('alpha_absolute') = 'alphaabs';
variant_map('beta_absolute') = 'betaabs';
variant_map('delta_absolute') = 'deltaabs';
variant_map('theta_absolute') = 'thetaabs';
variant_map('gamma_absolute') = 'gammaabs';
variant_map('alpha_relative') = 'alpharel';
variant_map('beta_relative') = 'betarel';
variant_map('theta_relative') = 'thetarel';
variant_map('delta_relative') = 'deltarel';

% 动态流列表
streams = struct('name', {}, 'num_channels', {}, 'colors', {}, ...
                 'buffer_time', {}, 'buffer_values', {}, ...   % 保留用于历史加载
                 'ylim', {}, 'ax', {}, 'lines', {});          % 新增绘图句柄

% 全局状态
current_stream_name = '';
is_recording = false;
fileID = -1;
recorded_file_path = '';
start_time = tic;

% 创建图形窗口
fig = figure('Name', '自动发现OSC数据流', 'Position', [100 100 1200 900]);
fig.UserData = struct(...
    'popup', [], 'ax', [], 'lines', [], ...      % 改为存储当前流的句柄
    'current_name', current_stream_name, ...
    'is_recording', false, 'fileID', -1, ...
    'recorded_file_path', '', ...
    'start_time', start_time, ...
    'timer_text', [], ...
    'record_start_time', 0, ...
    'last_timer_update', 0);

createControlPanel();

%% UDP 设置
try
    if isempty(local_host)
        u = udpport("datagram", 'LocalPort', udp_port, 'Timeout', 0.01);
    else
        u = udpport("datagram", 'LocalPort', udp_port, 'LocalHost', local_host, 'Timeout', 0.01);
    end
    fprintf('UDP 监听端口：%d，本地地址：%s\n', udp_port, iif(isempty(local_host), '所有接口', local_host));
catch ME
    error('UDP创建失败：%s\n请检查端口是否被占用或IP地址是否有效。', ME.message);
end

fprintf('等待 OSC 数据包...\n');
fprintf('新地址出现时将自动添加到下拉菜单，历史流将保留。\n');
fprintf('点击"开始存储"选择目录并输入文件名记录当前显示的流数据。\n');
fprintf('数据包格式：纯浮点数列表，若第一个参数为字符串时间戳则自动跳过。\n\n');

%% 实时主循环
packet_counter = 0;
while ishandle(fig)
    if u.NumDatagramsAvailable > 0
        dgram = read(u, 1);
        if isstruct(dgram) || isobject(dgram)
            raw_data = dgram.Data;
        else
            raw_data = dgram;
        end
        raw_data = uint8(raw_data);
        if isempty(raw_data) || ~isnumeric(raw_data)
            continue;
        end
        
        packet_counter = packet_counter + 1;
        
        [addr_str, float_vals] = parseOSC(raw_data);
        if isempty(addr_str) || isempty(float_vals)
            if DEBUG_MODE && mod(packet_counter, 100) == 1
                fprintf('[%d] 解析失败\n', packet_counter);
            end
            continue;
        end
        
        idx = findStreamIndex(addr_str, streams);
        if idx == 0
            % 新流：自动添加
            num_ch = length(float_vals);
            colors = generateColors(num_ch);
            
            candidate = extractSignalName(addr_str);
            ylim_range = [];
            if ~isempty(candidate)
                if isKey(variant_map, candidate)
                    key = variant_map(candidate);
                else
                    key = candidate;
                end
                if isKey(preset_map, key)
                    ylim_range = preset_map(key);
                    fprintf('  匹配预设信号 "%s" -> Y轴范围 [%.2f, %.2f]\n', addr_str, ylim_range(1), ylim_range(2));
                else
                    fprintf('  流 "%s" 无预设范围，将使用自适应Y轴\n', addr_str);
                end
            else
                fprintf('  流 "%s" 无法提取有效名称，使用自适应Y轴\n', addr_str);
            end
            
            streams(end+1) = struct(...
                'name', addr_str, ...
                'num_channels', num_ch, ...
                'colors', {colors}, ...
                'buffer_time', [], ...
                'buffer_values', zeros(0, num_ch), ...
                'ylim', ylim_range, ...
                'ax', [], ...
                'lines', []);
            idx = length(streams);
            if DEBUG_MODE
                fprintf('[%d] 发现新流: "%s", 通道数=%d\n', packet_counter, addr_str, num_ch);
            end
            updatePopupMenu();
            if isempty(current_stream_name)
                current_stream_name = addr_str;
                fig.UserData.current_name = current_stream_name;
                createStreamPlots(idx);
                loadStreamHistory(idx);
                updateTimeWindow(idx);
                drawnow;
            end
        else
            num_ch = streams(idx).num_channels;
            if length(float_vals) < num_ch
                float_vals = [float_vals, zeros(1, num_ch - length(float_vals))];
            elseif length(float_vals) > num_ch
                float_vals = float_vals(1:num_ch);
            end
        end
        
        num_ch = streams(idx).num_channels;
        sensor_vals = float_vals;
        timestamp_sec = posixtime(datetime('now'));
        sensor_vals(isnan(sensor_vals)) = 0;
        current_abs_time = toc(fig.UserData.start_time);
        
        % 更新缓冲区（用于历史加载）
        updateBuffer(idx, current_abs_time, sensor_vals);
        
        if DEBUG_MODE && mod(packet_counter, 100) == 1
            fprintf('[%d] 流: "%s", 数据范围: [%.2f, %.2f]\n', ...
                packet_counter, addr_str, min(sensor_vals), max(sensor_vals));
        end
        
        % 更新图形（使用 animatedline）
        if strcmp(current_stream_name, addr_str)
            lines = streams(idx).lines;
            ax = streams(idx).ax;
            for ch = 1:num_ch
                addpoints(lines(ch), current_abs_time, sensor_vals(ch));
                % 滑动 X 轴
                xlim(ax(ch), [current_abs_time - window_time, current_abs_time]);
                
                % 自适应 Y 轴（仅当没有固定范围时）
                if isempty(streams(idx).ylim)
                    [~, y] = getpoints(lines(ch));
                    if ~isempty(y)
                        ymin = min(y);
                        ymax = max(y);
                        if ymax == ymin
                            ylim(ax(ch), [ymin-1, ymax+1]);
                        else
                            yrange = ymax - ymin;
                            ylim(ax(ch), [ymin - 0.1*yrange, ymax + 0.1*yrange]);
                        end
                    end
                end
            end
            drawnow limitrate;
        end
        
        % 存储数据
        if fig.UserData.is_recording && strcmp(current_stream_name, addr_str)
            if fig.UserData.fileID ~= -1
                fprintf(fig.UserData.fileID, '%.6f', timestamp_sec);
                for ch = 1:num_ch
                    fprintf(fig.UserData.fileID, ',%.6f', sensor_vals(ch));
                end
                fprintf(fig.UserData.fileID, '\n');
                if DEBUG_MODE && mod(packet_counter, 100) == 0
                    fprintf('已写入 %d 个数据点到文件 %s\n', packet_counter, recorded_file_path);
                end
            else
                warning('文件句柄无效，记录已停止');
                fig.UserData.is_recording = false;
            end
        end
    else
        pause(0.001);  % 降低空闲等待，提高响应
    end
    
    % 更新计时显示
    if fig.UserData.is_recording
        current_time = toc(fig.UserData.record_start_time);
        if current_time - fig.UserData.last_timer_update >= 0.1
            if current_time >= 3600
                hours = floor(current_time / 3600);
                minutes = floor(mod(current_time, 3600) / 60);
                seconds = mod(current_time, 60);
                set(fig.UserData.timer_text, 'String', sprintf('记录时长: %02d:%02d:%02d', hours, minutes, seconds));
            else
                minutes = floor(current_time / 60);
                seconds = mod(current_time, 60);
                set(fig.UserData.timer_text, 'String', sprintf('记录时长: %02d:%02d', minutes, seconds));
            end
            fig.UserData.last_timer_update = current_time;
        end
    end
end

%% 退出清理
if fig.UserData.is_recording && fig.UserData.fileID ~= -1
    fclose(fig.UserData.fileID);
end
delete(u);
fprintf('\n程序已退出，共接收 %d 个数据包。\n', packet_counter);

%% ==================== 辅助函数 ====================

    function out = iif(cond, t, f)
        if cond
            out = t;
        else
            out = f;
        end
    end

    function candidate = extractSignalName(stream_name)
        parts = strsplit(stream_name, '/');
        if isempty(parts)
            candidate = '';
            return;
        end
        last_part = lower(parts{end});
        last_part = regexprep(last_part, '[^a-z0-9_]', '');
        candidate = last_part;
    end

    function createControlPanel()
        if isempty(streams)
            str_list = {'等待数据...'};
        else
            str_list = {streams.name};
        end
        fig.UserData.popup = uicontrol('Style', 'popupmenu', ...
            'String', str_list, ...
            'Position', [70, 850, 200, 30], 'Callback', @switchStream);
        if ~isempty(current_stream_name)
            idx = find(strcmp(str_list, current_stream_name));
            if ~isempty(idx)
                set(fig.UserData.popup, 'Value', idx);
            end
        end
        uicontrol('Style','text','Position',[20,850,50,30],'String','选择流:');
        uicontrol('Style','pushbutton','String','开始存储','Position',[800,850,80,30],'Callback',@startRecording);
        uicontrol('Style','pushbutton','String','结束存储','Position',[900,850,80,30],'Callback',@stopRecording);
        uicontrol('Style','pushbutton','String','自适应','Position',[1000,850,80,30],'Callback',@resetYAxes);
        fig.UserData.timer_text = uicontrol('Style', 'text', 'String', '记录时长: 00:00', ...
            'Position', [600, 850, 150, 30], 'HorizontalAlignment', 'left');
    end

    function updatePopupMenu()
        if isempty(streams)
            new_strings = {'等待数据...'};
        else
            new_strings = {streams.name};
        end
        set(fig.UserData.popup, 'String', new_strings);
        if ~isempty(current_stream_name)
            idx = find(strcmp(new_strings, current_stream_name));
            if ~isempty(idx)
                set(fig.UserData.popup, 'Value', idx);
            else
                set(fig.UserData.popup, 'Value', 1);
            end
        else
            set(fig.UserData.popup, 'Value', 1);
        end
    end

    function switchStream(~,~)
        if fig.UserData.is_recording
            warndlg('请先结束存储再切换流');
            restorePopupSelection();
            return;
        end
        popup = fig.UserData.popup;
        str_list = get(popup, 'String');
        val = get(popup, 'Value');
        if val > length(str_list) || val < 1
            return;
        end
        new_name = str_list{val};
        if strcmp(new_name, '等待数据...')
            return;
        end
        if strcmp(current_stream_name, new_name)
            return;
        end
        current_stream_name = new_name;
        fig.UserData.current_name = current_stream_name;
        idx = findStreamIndex(current_stream_name, streams);
        if idx == 0
            return;
        end
        clf(fig);
        createControlPanel();
        createStreamPlots(idx);
        loadStreamHistory(idx);
        updateTimeWindow(idx);
        drawnow;
    end

    function restorePopupSelection()
        if ~isempty(current_stream_name)
            str_list = get(fig.UserData.popup, 'String');
            idx = find(strcmp(str_list, current_stream_name));
            if ~isempty(idx)
                set(fig.UserData.popup, 'Value', idx);
            end
        end
    end

    function createStreamPlots(idx)
        % 创建 animatedline 子图，模仿 LSL 风格
        ch = streams(idx).num_channels;
        ax = gobjects(1,ch);
        lines = gobjects(1,ch);
        ylim_cfg = streams(idx).ylim;
        colors = streams(idx).colors;
        for i = 1:ch
            ax(i) = subplot(ch,1,i);
            title(sprintf('%s - 通道%d', streams(idx).name, i));
            grid on; hold on;
            xlim([0 window_time]);
            if isempty(ylim_cfg)
                ylim(ax(i), [-1, 1]);
            else
                ylim(ax(i), ylim_cfg);
            end
            lines(i) = animatedline(ax(i), 'Color', colors{i}, 'LineWidth', 1, ...
                                    'MaximumNumPoints', MAX_POINTS_PER_LINE);
        end
        streams(idx).ax = ax;
        streams(idx).lines = lines;
        fig.UserData.ax = ax;      % 兼容旧代码，但实际不再使用
        fig.UserData.lines = lines;
    end

    function loadStreamHistory(idx)
        % 将缓冲区历史数据加载到 animatedline 中
        t = streams(idx).buffer_time;
        v = streams(idx).buffer_values;
        if isempty(t)
            return;
        end
        lines = streams(idx).lines;
        for i = 1:size(v,2)
            % 逐点添加历史数据（避免一次性大量点导致卡顿，但历史数据通常不多）
            for j = 1:length(t)
                addpoints(lines(i), t(j), v(j,i));
            end
        end
    end

    function updateTimeWindow(idx)
        % 滑动当前 X 轴到最新时间
        if isempty(streams(idx).buffer_time)
            return;
        end
        latest_time = streams(idx).buffer_time(end);
        ax = streams(idx).ax;
        for i = 1:length(ax)
            xlim(ax(i), [latest_time - window_time, latest_time]);
        end
    end

    function updateBuffer(idx, t, vals)
        % 保留用于历史加载（切换流时恢复曲线）
        if isempty(streams(idx).buffer_time)
            streams(idx).buffer_time = t;
            streams(idx).buffer_values = vals(:)';
        else
            current_cols = size(streams(idx).buffer_values, 2);
            expected_cols = length(vals);
            if current_cols ~= expected_cols
                warning('流 %s 通道数从 %d 变为 %d，清空缓冲区', streams(idx).name, current_cols, expected_cols);
                streams(idx).buffer_time = t;
                streams(idx).buffer_values = vals(:)';
                return;
            end
            streams(idx).buffer_time = [streams(idx).buffer_time; t];
            streams(idx).buffer_values = [streams(idx).buffer_values; vals(:)'];
        end
        % 按时间窗口裁剪缓冲区（保持内存可控）
        valid = streams(idx).buffer_time >= t - window_time;
        streams(idx).buffer_time = streams(idx).buffer_time(valid);
        streams(idx).buffer_values = streams(idx).buffer_values(valid, :);
    end

    function resetYAxes(~,~)
        idx = findStreamIndex(current_stream_name, streams);
        if idx == 0
            return;
        end
        ylim_cfg = streams(idx).ylim;
        ax = streams(idx).ax;
        lines = streams(idx).lines;
        for i = 1:length(ax)
            if isempty(ylim_cfg)
                [~, y] = getpoints(lines(i));
                if ~isempty(y)
                    ymin = min(y);
                    ymax = max(y);
                    if ymax == ymin
                        ylim(ax(i), [ymin-1, ymax+1]);
                    else
                        yrange = ymax - ymin;
                        ylim(ax(i), [ymin - 0.1*yrange, ymax + 0.1*yrange]);
                    end
                else
                    ylim(ax(i), [-1, 1]);
                end
            else
                ylim(ax(i), ylim_cfg);
            end
        end
        drawnow;
        fprintf('已重置 "%s" 的Y轴模式\n', current_stream_name);
    end

    function startRecording(~,~)
        if fig.UserData.is_recording
            fprintf('已经在记录中，无需重复开始。\n');
            return;
        end
        if isempty(current_stream_name)
            warndlg('没有可记录的流');
            return;
        end
        
        dir_name = uigetdir(pwd, '选择保存目录');
        if dir_name == 0
            fprintf('用户取消目录选择，未开始记录。\n');
            return;
        end
        
        default_filename = sprintf('%s_%s.csv', strrep(current_stream_name, '/', '_'), datestr(now,'yyyymmdd_HHMMSS'));
        answer = inputdlg('输入保存文件名（.csv）:', '保存数据', [1 50], {default_filename});
        if isempty(answer)
            fprintf('用户取消文件名输入，未开始记录。\n');
            return;
        end
        filename = answer{1};
        if ~endsWith(filename, '.csv')
            filename = [filename, '.csv'];
        end
        
        fullpath = fullfile(dir_name, filename);
        fid = fopen(fullpath, 'w');
        if fid == -1
            errordlg(sprintf('文件创建失败：%s\n请检查路径权限。', fullpath));
            return;
        end
        
        fprintf(fid, 'Timestamp_sec');
        idx = findStreamIndex(current_stream_name, streams);
        if idx == 0
            fclose(fid);
            errordlg('无法找到当前流，记录失败');
            return;
        end
        for i = 1:streams(idx).num_channels
            fprintf(fid, ',Ch%d', i);
        end
        fprintf(fid, '\n');
        
        fig.UserData.fileID = fid;
        fig.UserData.recorded_file_path = fullpath;
        recorded_file_path = fullpath;
        fig.UserData.is_recording = true;
        fig.UserData.record_start_time = tic;
        fig.UserData.last_timer_update = 0;
        set(fig.UserData.timer_text, 'String', '记录时长: 00:00');
        set(fig.UserData.popup, 'Enable', 'off');
        fprintf('开始记录数据到文件：%s\n', fullpath);
    end

    function stopRecording(~,~)
        if ~fig.UserData.is_recording
            fprintf('当前没有进行中的记录。\n');
            return;
        end
        if fig.UserData.fileID ~= -1
            fclose(fig.UserData.fileID);
            fig.UserData.fileID = -1;
        end
        fig.UserData.is_recording = false;
        set(fig.UserData.popup, 'Enable', 'on');
        set(fig.UserData.timer_text, 'String', '记录时长: 00:00');
        fprintf('记录已停止，文件保存在：%s\n', recorded_file_path);
    end

    function idx = findStreamIndex(name, streams)
        idx = 0;
        for i = 1:length(streams)
            if strcmp(streams(i).name, name)
                idx = i;
                return;
            end
        end
    end

    function colors = generateColors(num_channels)
        defaultColors = {[0 0.4470 0.7410], [0.8500 0.3250 0.0980], [0.4660 0.6740 0.1880], ...
                         [0.9290 0.6940 0.1250], [0.4940 0.1840 0.5560], [0.3010 0.7450 0.9330], ...
                         [0.6350 0.0780 0.1840], [0 0 0], [0.5 0.5 0.5], [0.75 0 0.75]};
        colors = cell(num_channels, 1);
        for i = 1:num_channels
            colors{i} = defaultColors{mod(i-1, length(defaultColors)) + 1};
        end
    end

    function [addr, vals] = parseOSC(data)
        addr = '';
        vals = [];
        if ~isnumeric(data)
            return;
        end
        e = find(data == 0, 1);
        if isempty(e)
            return;
        end
        addr = char(data(1:e-1));
        s = ceil(e/4)*4 + 1;
        e2 = find(data(s:end) == 0, 1) + s - 1;
        if isempty(e2)
            return;
        end
        type = char(data(s:e2-1));
        if type(1) ~= ','
            return;
        end
        pos = ceil((e2 - s + 1)/4)*4 + ceil(e/4)*4 + 1;
        if length(type) > 1 && type(2) == 's'
            se = find(data(pos:end) == 0, 1) + pos - 1;
            if isempty(se)
                return;
            end
            pos = pos + ceil((se - pos + 1)/4)*4;
            type = type(3:end);
        else
            type = type(2:end);
        end
        for k = 1:length(type)
            if pos + 3 > length(data)
                break;
            end
            if type(k) == 'f'
                val_uint32 = typecast(data(pos:pos+3), 'uint32');
                val_uint32_swapped = swapbytes(val_uint32);
                val = double(typecast(val_uint32_swapped, 'single'));
                vals = [vals, val];
                pos = pos + 4;
            elseif type(k) == 'i'
                val_uint32 = typecast(data(pos:pos+3), 'uint32');
                val_uint32_swapped = swapbytes(val_uint32);
                val = double(typecast(val_uint32_swapped, 'int32'));
                vals = [vals, val];
                pos = pos + 4;
            else
                pos = pos + 4;
            end
        end
    end
end