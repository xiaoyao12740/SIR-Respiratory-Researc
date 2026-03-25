function main()
%主函数
clear;clc;close all;
%图形设置
set(groot,'defaultFigureToolBar','none');
set(groot,'defaultFigureMenuBar','none');
%数据加载
data_file='周报原始数据表.csv';
if ~exist(data_file,'file')
    error('数据文件 %s 未找到，请确保文件位于当前目录。',data_file);
end
data=readtable(data_file);
%必要字段检查
requiredVars={'year','week','south_ili','north_ili','south_tests','south_pos','north_tests','north_pos'};
missingVars=setdiff(requiredVars,data.Properties.VariableNames);
if ~isempty(missingVars)
    error('数据文件缺少必要字段：%s',strjoin(missingVars,', '));
end
%提取各列
year=data.year;
week=data.week;
south_ili=data.south_ili;%单位：%
north_ili=data.north_ili;
south_tests=data.south_tests;
south_pos=data.south_pos;
north_tests=data.north_tests;
north_pos=data.north_pos;
%中文变量说明
fprintf('====================================================================\n');
fprintf('                        流感监测数据总览（多年份）\n');
fprintf('====================================================================\n\n');
var_names={
    'year','年份','年份（例如2024,2025）';
    'week','周次','周次（1-52）';
    'south_ili','南方ILI%','南方哨点医院流感样病例就诊比例（%）';
    'north_ili','北方ILI%','北方哨点医院流感样病例就诊比例（%）';
    'south_tests','南方检测数','南方流感监测网络实验室检测样本数（份）';
    'south_pos','南方阳性数','南方检测阳性标本数（份）';
    'north_tests','北方检测数','北方流感监测网络实验室检测样本数（份）';
    'north_pos','北方阳性数','北方检测阳性标本数（份）';
    };
fprintf('数据变量说明：\n');
for i=1:size(var_names,1)
    fprintf('  %-10s（%-12s）：%s\n',var_names{i,2},var_names{i,1},var_names{i,3});
end
fprintf('\n数据记录总数：%d 行\n',height(data));
fprintf('包含年份：%s\n\n',strjoin(string(unique(year))',', '));
%数据排序与"连续时间轴"构造
data=sortrows(data,{'year','week'});
%提取数据
year=data.year;
week=data.week;
south_ili=data.south_ili;
north_ili=data.north_ili;
south_tests=data.south_tests;
south_pos=data.south_pos;
north_tests=data.north_tests;
north_pos=data.north_pos;
%构造连续周索引 t=1...N
t=(1:height(data))';
%数据转换与衍生变量计算
south_ili_ratio=south_ili / 100;
north_ili_ratio=north_ili / 100;
south_pos_rate=nan(size(south_pos));
north_pos_rate=nan(size(north_pos));
south_pos_rate(south_tests > 0)=south_pos(south_tests > 0) ./ south_tests(south_tests > 0);
north_pos_rate(north_tests > 0)=north_pos(north_tests > 0) ./ north_tests(north_tests > 0);
south_I_obs=south_ili_ratio .* south_pos_rate;
north_I_obs=north_ili_ratio .* north_pos_rate;
%数据完整性与合理性检查
fprintf('--- 完整性与合理性检查 ---\n');
%缺失值统计
fprintf('缺失值统计（NaN）：\n');
fprintf('  south_ili:   %d\n',sum(isnan(south_ili)));
fprintf('  north_ili:   %d\n',sum(isnan(north_ili)));
fprintf('  south_tests: %d\n',sum(isnan(south_tests)));
fprintf('  south_pos:   %d\n',sum(isnan(south_pos)));
fprintf('  north_tests: %d\n',sum(isnan(north_tests)));
fprintf('  north_pos:   %d\n',sum(isnan(north_pos)));
%逻辑一致性检查
bad1=find(south_pos > south_tests & ~isnan(south_pos) & ~isnan(south_tests));
bad2=find(north_pos > north_tests & ~isnan(north_pos) & ~isnan(north_tests));
if ~isempty(bad1) || ~isempty(bad2)
    warning('发现阳性数 > 检测数的异常行：南方%d行，北方%d行。请检查数据。',numel(bad1),numel(bad2));
else
    fprintf('逻辑一致性：未发现"阳性数 > 检测数"的异常。\n');
end
z1=sum(south_tests==0);
z2=sum(north_tests==0);
if z1 > 0 || z2 > 0
    warning('存在检测数为0：南方%d行，北方%d行。对应阳性率已置为NaN。',z1,z2);
else
    fprintf('检测数检查：未发现检测数为0。\n');
end
years=unique(year);
for yi=1:numel(years)
    y=years(yi);
    wk=week(year==y);
    missW=setdiff(1:52,unique(wk));
    if ~isempty(missW)
        warning('年份 %d 缺失周次：%s',y,strjoin(string(missW),', '));
    else
        fprintf('年份 %d 周次完整（1-52齐全）。\n',y);
    end
end
fprintf('\n');
%基础统计描述（按年份）并保存为表格
fprintf('--- 描述性统计（按年份）---\n');
%创建用于保存统计信息的表格
statsTable=table();
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    fprintf('\n【%d 年】\n',y);
    %南方
    south_ili_min=min(south_ili(idx));
    south_ili_max=max(south_ili(idx));
    south_pos_min=min(south_pos_rate(idx))*100;
    south_pos_max=max(south_pos_rate(idx))*100;
    south_I_obs_min=min(south_I_obs(idx));
    south_I_obs_max=max(south_I_obs(idx));
    fprintf('  南方：ILI%%范围 %.2f%%~%.2f%%；阳性率范围 %.2f%%~%.2f%%；I_obs范围 %.4f~%.4f\n',...
        south_ili_min,south_ili_max,south_pos_min,south_pos_max,south_I_obs_min,south_I_obs_max);
    %北方
    north_ili_min=min(north_ili(idx));
    north_ili_max=max(north_ili(idx));
    north_pos_min=min(north_pos_rate(idx))*100;
    north_pos_max=max(north_pos_rate(idx))*100;
    north_I_obs_min=min(north_I_obs(idx));
    north_I_obs_max=max(north_I_obs(idx));
    fprintf('  北方：ILI%%范围 %.2f%%~%.2f%%；阳性率范围 %.2f%%~%.2f%%；I_obs范围 %.4f~%.4f\n',...
        north_ili_min,north_ili_max,north_pos_min,north_pos_max,north_I_obs_min,north_I_obs_max);
    %添加到统计表
    row=table(y,...
        south_ili_min,south_ili_max,south_pos_min,south_pos_max,south_I_obs_min,south_I_obs_max,...
        north_ili_min,north_ili_max,north_pos_min,north_pos_max,north_I_obs_min,north_I_obs_max,...
        'VariableNames',{'年份',...
        '南方ILI%_min','南方ILI%_max','南方阳性率%_min','南方阳性率%_max','南方I_obs_min','南方I_obs_max',...
        '北方ILI%_min','北方ILI%_max','北方阳性率%_min','北方阳性率%_max','北方I_obs_min','北方I_obs_max'});
    statsTable=[statsTable;row];
end
fprintf('\n====================================================================\n\n');
%打印数据明细
fprintf('全部数据明细（完整输出）：\n\n');
fprintf('%-6s %-6s %-10s %-10s %-10s %-10s %-10s %-10s\n',...
    '年份','周次','南方ILI%','北方ILI%','南方检测','南方阳性','北方检测','北方阳性');
for i=1:height(data)
    fprintf('%-6d W%02d   %-10.1f %-10.1f %-10d %-10d %-10d %-10d\n',...
        year(i),week(i),...
        south_ili(i),north_ili(i),...
        south_tests(i),south_pos(i),...
        north_tests(i),north_pos(i));
end
%创建保存图片的文件夹
output_folder='数据预览图';
if ~exist(output_folder,'dir')
    mkdir(output_folder);
end
%绘制并保存预览图（连续时间轴组合图+子图）
%组合图1：连续时间轴（ILI%，阳性率，I_obs，检测量）
fig1=figure('Name','流感监测数据预览（多年份）','Position',[100,100,1300,700]);
%子图1：ILI%
subplot(2,2,1);
plot(t,south_ili,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_ili,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('ILI%');
title('ILI%（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
%子图2：阳性率
subplot(2,2,2);
plot(t,south_pos_rate*100,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_pos_rate*100,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('阳性率 (%)');
title('阳性率（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
%子图3：I_obs
subplot(2,2,3);
plot(t,south_I_obs,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_I_obs,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('I_{obs}');
title('I_{obs}=ILI比例×阳性率（感染规模代理）');
legend('南方','北方','Location','best');
grid on;
%子图4：检测量
subplot(2,2,4);
bar(t,[south_tests,north_tests],'stacked');
xlabel('连续周序号 t');ylabel('检测样本数');
title('检测样本量（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
%保存组合图1
exportgraphics(fig1,fullfile(output_folder,'01_连续时间轴组合图.png'),'Resolution',600);
%保存每个子图为单独图片
%子图1-1
f1=figure('Visible','on');
plot(t,south_ili,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_ili,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('ILI%');
title('ILI%（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
exportgraphics(f1,fullfile(output_folder,'01a_ILI%.png'),'Resolution',600);
close(f1);
%子图1-2
f2=figure('Visible','on');
plot(t,south_pos_rate*100,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_pos_rate*100,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('阳性率 (%)');
title('阳性率（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
exportgraphics(f2,fullfile(output_folder,'01b_阳性率.png'),'Resolution',600);
close(f2);
%子图1-3
f3=figure('Visible','on');
plot(t,south_I_obs,'b-o','LineWidth',1.2,'MarkerSize',3);hold on;
plot(t,north_I_obs,'r-s','LineWidth',1.2,'MarkerSize',3);
xlabel('连续周序号 t');ylabel('I_{obs}');
title('I_{obs}=ILI比例×阳性率（感染规模代理）');
legend('南方','北方','Location','best');
grid on;
exportgraphics(f3,fullfile(output_folder,'01c_Iobs.png'),'Resolution',600);
close(f3);
%子图1-4
f4=figure('Visible','on');
bar(t,[south_tests,north_tests],'stacked');
xlabel('连续周序号 t');ylabel('检测样本数');
title('检测样本量（跨年份连续序列）');
legend('南方','北方','Location','best');
grid on;
exportgraphics(f4,fullfile(output_folder,'01d_检测量.png'),'Resolution',600);
close(f4);
%年对比图
fig2=figure('Name','分年对比（同周次）','Position',[120,120,1300,700]);
colors=lines(numel(years));
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    %ILI%
    subplot(2,2,1);hold on;
    plot(week(idx),south_ili(idx),'-o','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));
    subplot(2,2,2);hold on;
    plot(week(idx),north_ili(idx),'-s','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));
    %阳性率
    subplot(2,2,3);hold on;
    plot(week(idx),south_pos_rate(idx)*100,'-o','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));
    subplot(2,2,4);hold on;
    plot(week(idx),north_pos_rate(idx)*100,'-s','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));
end
subplot(2,2,1);grid on;xlabel('周次');ylabel('ILI%');title('南方 ILI%（按年对比）');
legend(strcat(string(years),"年"),'Location','best');
subplot(2,2,2);grid on;xlabel('周次');ylabel('ILI%');title('北方 ILI%（按年对比）');
legend(strcat(string(years),"年"),'Location','best');
subplot(2,2,3);grid on;xlabel('周次');ylabel('阳性率(%)');title('南方 阳性率（按年对比）');
legend(strcat(string(years),"年"),'Location','best');
subplot(2,2,4);grid on;xlabel('周次');ylabel('阳性率(%)');title('北方 阳性率（按年对比）');
legend(strcat(string(years),"年"),'Location','best');
%保存组合图2
exportgraphics(fig2,fullfile(output_folder,'02_分年对比组合图.png'),'Resolution',600);
%保存每个子图为单独图片
%子图2-1：南方ILI%
f21=figure('Visible','on');
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    plot(week(idx),south_ili(idx),'-o','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));hold on;
end
xlabel('周次');ylabel('ILI%');title('南方 ILI%（按年对比）');
legend(strcat(string(years),"年"),'Location','best');grid on;
exportgraphics(f21,fullfile(output_folder,'02a_南方ILI对比.png'),'Resolution',600);
close(f21);
%子图2-2：北方ILI%
f22=figure('Visible','on');
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    plot(week(idx),north_ili(idx),'-s','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));hold on;
end
xlabel('周次');ylabel('ILI%');title('北方 ILI%（按年对比）');
legend(strcat(string(years),"年"),'Location','best');grid on;
exportgraphics(f22,fullfile(output_folder,'02b_北方ILI对比.png'),'Resolution',600);
close(f22);
%子图2-3：南方阳性率
f23=figure('Visible','on');
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    plot(week(idx),south_pos_rate(idx)*100,'-o','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));hold on;
end
xlabel('周次');ylabel('阳性率(%)');title('南方 阳性率（按年对比）');
legend(strcat(string(years),"年"),'Location','best');grid on;
exportgraphics(f23,fullfile(output_folder,'02c_南方阳性率对比.png'),'Resolution',600);
close(f23);
%子图2-4：北方阳性率
f24=figure('Visible','on');
for yi=1:numel(years)
    y=years(yi);
    idx=(year==y);
    plot(week(idx),north_pos_rate(idx)*100,'-s','LineWidth',1.2,'MarkerSize',3,'Color',colors(yi,:));hold on;
end
xlabel('周次');ylabel('阳性率(%)');title('北方 阳性率（按年对比）');
legend(strcat(string(years),"年"),'Location','best');grid on;
exportgraphics(f24,fullfile(output_folder,'02d_北方阳性率对比.png'),'Resolution',600);
close(f24);
%保存统计表格
writetable(statsTable,fullfile(output_folder,'描述性统计表.xlsx'));
fprintf('描述性统计表已保存至 %s\n',fullfile(output_folder,'描述性统计表.xlsx'));
diary_file=fullfile(output_folder,'数据明细.txt');
diary(diary_file);
fprintf('全部数据明细：\n\n');
fprintf('%-6s %-6s %-10s %-10s %-10s %-10s %-10s %-10s\n',...
    '年份','周次','南方ILI%','北方ILI%','南方检测','南方阳性','北方检测','北方阳性');
for i=1:height(data)
    fprintf('%-6d W%02d   %-10.1f %-10.1f %-10d %-10d %-10d %-10d\n',...
        year(i),week(i),...
        south_ili(i),north_ili(i),...
        south_tests(i),south_pos(i),...
        north_tests(i),north_pos(i));
end
diary off;
fprintf('数据明细已保存至 %s\n',diary_file);
processed_data=table(year,week,t,...
    south_ili,north_ili,south_tests,south_pos,north_tests,north_pos,...
    south_ili_ratio,north_ili_ratio,...
    south_pos_rate,north_pos_rate,...
    south_I_obs,north_I_obs);
save('processed_data.mat','processed_data');
fprintf('\n处理后的数据已保存至 processed_data.mat\n');
fprintf('====================================================================\n');
end