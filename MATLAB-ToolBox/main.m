function main()

    % =========================
    % 🎨 主界面
    % =========================
    fig = uifigure('Name','Muse数据可视化与采集',...
        'Position',[300 150 700 450],...
        'Color',[0.94 0.94 0.94]);

    % ===== 标题 =====
    uilabel(fig,...
        'Text','数据流控制中心',...
        'FontSize',20,...
        'FontWeight','bold',...
        'Position',[250 400 300 30]);

    % =========================
    % 🎛️ 控制面板
    % =========================
    pnl = uipanel(fig,...
        'Title','模式选择',...
        'FontSize',12,...
        'Position',[50 120 200 250]);

    % ===== LSL按钮 =====
    btnLSL = uibutton(pnl,...
        'Text','启动 LSL',...
        'FontSize',14,...
        'Position',[30 150 140 40],...
        'ButtonPushedFcn',@(btn,event)runLSL());

    % ===== OSC按钮 =====
    btnOSC = uibutton(pnl,...
        'Text','启动 OSC',...
        'FontSize',14,...
        'Position',[30 80 140 40],...
        'ButtonPushedFcn',@(btn,event)runOSC());

    % ===== 退出按钮 =====
    btnExit = uibutton(pnl,...
        'Text','退出',...
        'FontSize',12,...
        'Position',[30 20 140 35],...
        'ButtonPushedFcn',@(btn,event)close(fig));

    % =========================
    % 📋 日志区
    % =========================
    logArea = uitextarea(fig,...
        'Position',[280 50 380 320],...
        'Editable','off',...
        'FontName','Consolas');

    % =========================
    % 🧠 功能函数
    % =========================

    function runLSL()

        appendLog('点击：启动 LSL');

        try
            appendLog('正在运行 LSL...');
            drawnow;

            lsl();   % 👉 直接调用你的 lsl.m

            appendLog('LSL 运行结束');

        catch ME
            appendLog(['LSL 错误: ' ME.message]);
        end

    end

    function runOSC()

        appendLog('点击：启动 OSC');

        try
            appendLog('正在运行 OSC...');
            drawnow;

            osc();   % 👉 直接调用你的 osc.m（内部已有端口）

            appendLog('OSC 运行结束');

        catch ME
            appendLog(['OSC 错误: ' ME.message]);
        end

    end

    % =========================
    % 📝 日志函数（稳定版）
    % =========================
    function appendLog(msg)

        try
            timeStr = char(datetime('now','Format','HH:mm:ss.SSS'));

            old = logArea.Value;

            if ischar(old)
                old = {old};
            end

            logArea.Value = [old; { [timeStr '  |  ' msg] }];

        catch
            disp(msg);
        end

    end

end