%SIR模型主函数
clear;clc;close all;
set(groot,'defaultFigureToolBar','none');
set(groot,'defaultFigureMenuBar','none');
%读取数据
data=readtable('周报原始数据表.csv');
year=data.year;
week=data.week;
south_ili=data.south_ili / 100;
north_ili=data.north_ili / 100;
south_tests=data.south_tests;
south_pos=data.south_pos;
north_tests=data.north_tests;
north_pos=data.north_pos;
%计算阳性率和观测感染规模I_obs
south_pos_rate=south_pos ./ south_tests;
north_pos_rate=north_pos ./ north_tests;
south_I_obs=south_ili .* south_pos_rate;
north_I_obs=north_ili .* north_pos_rate;
t=(1:length(week))';
%定义要分析的波次
wave1_start=find(year==2024 & week==40,1,'first');
wave1_end=find(year==2025 & week==10,1,'first');
wave2_start=find(year==2025 & week==35,1,'first');
wave2_end=find(year==2025 & week==52,1,'first');
if isempty(wave1_start) || isempty(wave1_end)
    error('波1的起止周次未找到，请检查周次范围。');
end
if isempty(wave2_start) || isempty(wave2_end)
    error('波2的起止周次未找到，请检查周次范围。');
end
waves=struct();
waves(1).name='2024-2025跨年波';
waves(1).idx=wave1_start:wave1_end;
waves(2).name='2025年末波';
waves(2).idx=wave2_start:wave2_end;
regions={'south','north'};
%创建总览图文件夹
if ~exist('总览图','dir')
    mkdir('总览图');
end
%预分配结果结构体
results=struct();
for w=1:length(waves)
    for r=1:length(regions)
        results(w,r).wave_name=waves(w).name;
        results(w,r).region=regions{r};
        results(w,r).t=[];
        results(w,r).I_obs=[];
        results(w,r).params=[];
        results(w,r).R0=[];
        results(w,r).residuals=[];
        results(w,r).RMSE=[];
        results(w,r).MAE=[];
        results(w,r).MAPE=[];
        results(w,r).R2=[];
        results(w,r).beta_ci=[];
        results(w,r).gamma_ci=[];
        results(w,r).R0_ci=[];
        results(w,r).vax_results=[];
        results(w,r).control_results=[];
        results(w,r).combo_results=[];%存储9种组合
    end
end
%拟合设置
options=optimoptions('lsqcurvefit','Display','off','MaxFunctionEvaluations',1e4,'MaxIterations',1000);
N=1;%总人口归一化
eff=0.8;%疫苗有效性（假设80%）
fprintf('\n%s\n',repmat('=',1,80));
fprintf('                  流感SIR模型多波次、南北分区分析（细化干预）\n');
fprintf('%s\n',repmat('=',1,80));
fprintf('波1选择24年的第40周到25年的第10周，即2024-2025跨年波\n');
fprintf('波2选择25年的第35-52周，即2025年年末波\n');
%循环拟合每个波次和区域
for w=1:length(waves)
    for r=1:length(regions)
        fprintf('\n--- 正在处理：%s，%s ---\n',waves(w).name,regions{r});
        %提取数据
        if strcmp(regions{r},'south')
            I_obs=south_I_obs(waves(w).idx);
        else
            I_obs=north_I_obs(waves(w).idx);
        end
        t_wave=(1:length(I_obs))';
        %数据统计
        fprintf('  数据长度: %d, 范围: [%.4f, %.4f], 均值: %.4f\n',...
            length(I_obs),min(I_obs),max(I_obs),mean(I_obs));
        %初始感染处理
        I0=I_obs(1);
        if I0==0
            I0=max(I_obs(I_obs>0));
            if isempty(I0),I0=1e-4;end
            fprintf('  警告：初始感染为0，已调整为 %.4f\n',I0);
        end
        %多起点拟合（50个随机起点）
        beta_range=[0.1,5];
        gamma_range=[0.1,2];
        a_range=[0.01,2];
        num_starts=50;
        best_params=[];
        best_resnorm=inf;
        for i=1:num_starts
            params0=[beta_range(1)+rand*range(beta_range),...
                       gamma_range(1)+rand*range(gamma_range),...
                       a_range(1)+rand*range(a_range)];
            lb=[0,0,0];
            ub=[10,10,10];
            try
                [p,resnorm]=fit_sir_quiet(t_wave,I_obs,params0,lb,ub,N,I0,options);
                if resnorm < best_resnorm && all(p>0)
                    best_resnorm=resnorm;
                    best_params=p;
                end
            catch
                continue;
            end
        end
        if isempty(best_params)
            error('模型拟合失败，请检查数据。');
        end
        %保存参数
        results(w,r).params=best_params;
        results(w,r).R0=best_params(1) / best_params(2);
        results(w,r).t=t_wave;
        results(w,r).I_obs=I_obs;
        %拟合曲线和误差
        I_fit=sir_simulate(best_params,t_wave,N,I0);
        results(w,r).I_fit=I_fit;
        residuals=I_obs-I_fit;
        results(w,r).residuals=residuals;
        results(w,r).RMSE=sqrt(mean(residuals.^2));
        results(w,r).MAE=mean(abs(residuals));
        mape_thr=1e-4;
        mask_mape=I_obs > mape_thr;
        if any(mask_mape)
            results(w,r).MAPE=mean(abs(residuals(mask_mape) ./ I_obs(mask_mape))) * 100;
        else
            results(w,r).MAPE=NaN;
        end
        results(w,r).R2=1-sum(residuals.^2) / sum((I_obs-mean(I_obs)).^2);
        %参数置信区间（基于渐近正态的参数不确定性分析）
        fitfun=@(params,t) sir_simulate(params,t,N,I0);
        [~,~,~,~,~,~,J]=lsqcurvefit(fitfun,best_params,t_wave,I_obs,lb,ub,options);
        if ~isempty(J)
            MSE=sum(residuals.^2) / (length(t_wave)-length(best_params));
            try
                cov_matrix=inv(J'*J) * MSE;
                n_sim=1000;
                params_sim=mvnrnd(best_params,cov_matrix,n_sim);
                valid=all(params_sim > 0,2);
                if sum(valid) > 50
                    beta_ci=quantile(params_sim(valid,1),[0.025 0.975]);
                    gamma_ci=quantile(params_sim(valid,2),[0.025 0.975]);
                    R0_sim=params_sim(valid,1) ./ params_sim(valid,2);
                    R0_ci=quantile(R0_sim,[0.025 0.975]);
                    results(w,r).beta_ci=beta_ci;
                    results(w,r).gamma_ci=gamma_ci;
                    results(w,r).R0_ci=R0_ci;
                end
            catch
                %协方差奇异，跳过
            end
        end
        %存储实际使用的I0（可能被修正过）
        results(w,r).I0_used=I0;
        %情景模拟（基线）
        y0=[N-I0,I0,0];
        [~,y_base]=ode45(@(t,y) sir_ode(t,y,best_params(1),best_params(2)),t_wave,y0);
        I_base=y_base(:,2)/N * best_params(3);
        results(w,r).I_base=I_base;
        %疫苗梯度（细化）
        v_list=[0,0.1,0.2,0.4];
        vax_results=[];
        for v=v_list
            S0_vax=N * (1-v*eff);
            y0_vax=[S0_vax,I0,N-S0_vax-I0];
            [~,y_v]=ode45(@(t,y) sir_ode(t,y,best_params(1),best_params(2)),t_wave,y0_vax);
            I_v=y_v(:,2)/N * best_params(3);
            vax_results=[vax_results;v,max(I_v),sum(I_v),sum(I_v)/sum(I_base)*100];
        end
        results(w,r).vax_results=vax_results;
        %管控梯度（细化）
        u_list=[0,0.1,0.2,0.4];
        control_results=[];
        for u=u_list
            beta_c=best_params(1) * (1-u);
            [~,y_c]=ode45(@(t,y) sir_ode(t,y,beta_c,best_params(2)),t_wave,y0);
            I_c=y_c(:,2)/N * best_params(3);
            control_results=[control_results;u,max(I_c),sum(I_c),sum(I_c)/sum(I_base)*100];
        end
        results(w,r).control_results=control_results;
        %组合情景（9种：疫苗0.1,0.2,0.4 × 管控0.1,0.2,0.4）
        combo_results=[];
        v_combo_list=[0.1,0.2,0.4];
        u_combo_list=[0.1,0.2,0.4];
        for vc=v_combo_list
            for uc=u_combo_list
                S0_combo=N * (1-vc*eff);
                beta_combo=best_params(1) * (1-uc);
                y0_combo=[S0_combo,I0,N-S0_combo-I0];
                [~,y_combo]=ode45(@(t,y) sir_ode(t,y,beta_combo,best_params(2)),t_wave,y0_combo);
                I_combo=y_combo(:,2)/N * best_params(3);
                combo_results=[combo_results;vc,uc,max(I_combo),sum(I_combo),sum(I_combo)/sum(I_base)*100];
            end
        end
        results(w,r).combo_results=combo_results;
        %打印当前模型的关键结果
        if ~isempty(results(w,r).beta_ci)
            fprintf('  β=%.4f [%.4f, %.4f], γ=%.4f [%.4f, %.4f], R₀=%.4f [%.4f, %.4f], a=%.4f, R²=%.4f, MAPE=%.2f%%\n',...
                best_params(1),results(w,r).beta_ci(1),results(w,r).beta_ci(2),...
                best_params(2),results(w,r).gamma_ci(1),results(w,r).gamma_ci(2),...
                results(w,r).R0,results(w,r).R0_ci(1),results(w,r).R0_ci(2),...
                best_params(3),results(w,r).R2,results(w,r).MAPE);
        else
            fprintf('  β=%.4f, γ=%.4f, R₀=%.4f, a=%.4f, R²=%.4f, MAPE=%.2f%%（CI不可用）\n',...
                best_params(1),best_params(2),results(w,r).R0,best_params(3),results(w,r).R2,results(w,r).MAPE);
        end
    end
end
fprintf('\n%s\n',repmat('=',1,80));
fprintf('模型参数意义说明：\n');
fprintf('  β：有效传播率，表示一个感染者每周接触易感者并导致感染的平均概率。\n');
fprintf('  γ：恢复率，感染者每周康复的比例，平均感染周期=1/γ 周。\n');
fprintf('  R₀=β/γ：基本再生数，表示在完全易感人群中一个感染者平均能传染的人数。\n');
fprintf('  a：尺度参数，将模型模拟的感染者比例映射到观测指标I_obs。\n');
fprintf('  R²：决定系数，衡量模型解释方差的比例，越接近1越好。\n');
fprintf('  MAPE：平均绝对百分比误差，反映相对误差大小。当观测值接近0时，MAPE可能异常增大，此时应参考RMSE和MAE。\n');
fprintf('  指标解释：\n');
fprintf('  RMSE (均方根误差)：衡量拟合值与观测值之间的平均误差，单位与I_obs相同。\n');
fprintf('  MAE (平均绝对误差)：绝对误差的平均值，单位与I_obs相同。\n');
fprintf('  峰值：模拟期间感染者比例的最大值（无量纲比例）。\n');
fprintf('  累计感染：整个流行期间感染者的累计比例（无量纲），等于∑I(t)。\n');
fprintf('  所有比例值均为相对于总人口的比例，若需实际人数，可乘以研究区域总人口。\n');
fprintf('%s\n',repmat('=',1,80));
%模型对比汇总表格
fprintf('\n%s\n',repmat('=',1,100));
fprintf('%-20s %-6s %-20s %-20s %-20s %-8s %-8s %-8s %-8s\n',...
    '波次','区域','β (95%CI)','γ (95%CI)','R₀ (95%CI)','a','R²','RMSE','MAE');
fprintf('%s\n',repmat('-',1,100));
T=table();
for w=1:length(waves)
    for r=1:length(regions)
        if ~isempty(results(w,r).beta_ci)
            beta_str=sprintf('%.4f [%.4f,%.4f]',results(w,r).params(1),results(w,r).beta_ci(1),results(w,r).beta_ci(2));
            gamma_str=sprintf('%.4f [%.4f,%.4f]',results(w,r).params(2),results(w,r).gamma_ci(1),results(w,r).gamma_ci(2));
            R0_str=sprintf('%.4f [%.4f,%.4f]',results(w,r).R0,results(w,r).R0_ci(1),results(w,r).R0_ci(2));
        else
            beta_str=sprintf('%.4f',results(w,r).params(1));
            gamma_str=sprintf('%.4f',results(w,r).params(2));
            R0_str=sprintf('%.4f',results(w,r).R0);
        end
        fprintf('%-20s %-6s %-20s %-20s %-20s %-8.4f %-8.4f %-8.4f %-8.4f\n',...
            waves(w).name,regions{r},beta_str,gamma_str,R0_str,...
            results(w,r).params(3),results(w,r).R2,results(w,r).RMSE,results(w,r).MAE);
        T=[T;table({waves(w).name},{regions{r}},{beta_str},{gamma_str},{R0_str},...
            results(w,r).params(3),results(w,r).R2,results(w,r).RMSE,results(w,r).MAE,...
            'VariableNames',{'波次','区域','β_95CI','γ_95CI','R0_95CI','a','R2','RMSE','MAE'})];
    end
end
fprintf('%s\n',repmat('-',1,100));
writetable(T,'模型参数对比表.xlsx');
fprintf('模型参数对比表已保存至模型参数对比表.xlsx\n');
%情景模拟结果表格（细化干预）
fprintf('\n%s\n',repmat('=',1,100));
fprintf('情景模拟结果（峰值下降百分比、累计感染下降百分比）\n');
fprintf('说明：所有峰值和累计感染均为相对于总人口的比例。\n');
fprintf('%s\n',repmat('-',1,100));
scenario_T=table();
for w=1:length(waves)
    for r=1:length(regions)
        fprintf('\n【%s-%s】\n',waves(w).name,regions{r});
        base_peak=results(w,r).vax_results(1,2);
        base_cum=results(w,r).vax_results(1,3);
        fprintf('基线：峰值=%.4f，累计感染=%.4f\n',base_peak,base_cum);
        %疫苗情景
        fprintf('疫苗情景（有效性80%）：\n');
        fprintf('  覆盖率    峰值        累计感染    峰值下降%%    累计感染%%\n');
        for i=2:size(results(w,r).vax_results,1)
            peak=results(w,r).vax_results(i,2);
            cum=results(w,r).vax_results(i,3);
            peak_pct=(base_peak-peak)/base_peak * 100;
            cum_pct=results(w,r).vax_results(i,4);
            fprintf('    %d%%        %.4f    %.4f    %.1f%%        %.1f%%\n',...
                results(w,r).vax_results(i,1)*100,peak,cum,peak_pct,cum_pct);
            %构造表格行：疫苗情景，管控强度填"/"
            v_str=sprintf('%d',results(w,r).vax_results(i,1)*100);
            u_str='/';
            scenario_T=[scenario_T;table({waves(w).name},{regions{r}},{'疫苗'},{v_str},{u_str},...
                peak,cum,peak_pct,cum_pct,...
                'VariableNames',{'波次','区域','干预类型','疫苗覆盖率','管控强度','峰值','累计感染','峰值下降百分比','累计感染百分比'})];
        end
        %管控情景
        fprintf('管控情景（传播率降低）：\n');
        fprintf('  强度      峰值        累计感染    峰值下降%%    累计感染%%\n');
        base_peak=results(w,r).control_results(1,2);
        base_cum=results(w,r).control_results(1,3);
        for i=2:size(results(w,r).control_results,1)
            peak=results(w,r).control_results(i,2);
            cum=results(w,r).control_results(i,3);
            peak_pct=(base_peak-peak)/base_peak * 100;
            cum_pct=results(w,r).control_results(i,4);
            fprintf('    %d%%        %.4f    %.4f    %.1f%%        %.1f%%\n',...
                results(w,r).control_results(i,1)*100,peak,cum,peak_pct,cum_pct);
            %构造表格行：管控情景，疫苗覆盖率填"/"
            v_str='/';
            u_str=sprintf('%d',results(w,r).control_results(i,1)*100);
            scenario_T=[scenario_T;table({waves(w).name},{regions{r}},{'管控'},{v_str},{u_str},...
                peak,cum,peak_pct,cum_pct,...
                'VariableNames',{'波次','区域','干预类型','疫苗覆盖率','管控强度','峰值','累计感染','峰值下降百分比','累计感染百分比'})];
        end
        %组合情景（9种）
        fprintf('组合情景（疫苗×管控）：\n');
        fprintf('  疫苗%%   管控%%   峰值        累计感染    峰值下降%%    累计感染%%\n');
        for j=1:size(results(w,r).combo_results,1)
            vc=results(w,r).combo_results(j,1);
            uc=results(w,r).combo_results(j,2);
            peak=results(w,r).combo_results(j,3);
            cum=results(w,r).combo_results(j,4);
            pct_cum=results(w,r).combo_results(j,5);
            peak_pct=(base_peak-peak)/base_peak * 100;
            fprintf('    %d%%      %d%%      %.4f    %.4f    %.1f%%        %.1f%%\n',...
                vc*100,uc*100,peak,cum,peak_pct,pct_cum);
            %构造表格行：组合情景，两者都是数字字符串
            v_str=sprintf('%d',vc*100);
            u_str=sprintf('%d',uc*100);
            scenario_T=[scenario_T;table({waves(w).name},{regions{r}},{'组合'},{v_str},{u_str},...
                peak,cum,peak_pct,pct_cum,...
                'VariableNames',{'波次','区域','干预类型','疫苗覆盖率','管控强度','峰值','累计感染','峰值下降百分比','累计感染百分比'})];
        end
    end
end
fprintf('%s\n',repmat('=',1,100));
writetable(scenario_T,'情景模拟结果表.xlsx');
fprintf('情景模拟结果表已保存至情景模拟结果表.xlsx\n');
%绘图：为每个模型创建文件夹并生成组合图与单子图
for w=1:length(waves)
    for r=1:length(regions)
        %创建模型专用文件夹
        folder_name=sprintf('%s_%s',waves(w).name,regions{r});
        if ~exist(folder_name,'dir')
            mkdir(folder_name);
        end
        %准备数据
        t_plot=results(w,r).t;
        I_obs=results(w,r).I_obs;
        I_fit=results(w,r).I_fit;
        residuals=results(w,r).residuals;
        params=results(w,r).params;
        I0_used=results(w,r).I0_used;
        I_base=results(w,r).I_base;
        beta=params(1);
        gamma=params(2);
        a=params(3);
        %检验（可选择性使用）
        fprintf('  起点检查: I_obs(1)=%.6g, I0_used=%.6g, I_fit(1)=%.6g, diff_fit-obs=%.3g\n',...
            I_obs(1),I0_used,I_fit(1),I_fit(1)-I_obs(1));
        fprintf('  基线一致性: max|I_fit-I_base|=%.3g\n',max(abs(I_fit-I_base)));
        %情景参数
        v_list_plot=[0.1,0.2,0.4];
        u_list_plot=[0.1,0.2,0.4];
        colors=lines(length(v_list_plot));
        %疫苗情景
        I_vax_all=cell(length(v_list_plot),1);
        for i=1:length(v_list_plot)
            v=v_list_plot(i);
            S0_vax=N * (1-v*eff);
            y0_vax=[S0_vax,I0_used,N-S0_vax-I0_used];
            [~,y_v]=ode45(@(t,y) sir_ode(t,y,beta,gamma),t_plot,y0_vax);
            I_vax_all{i}=y_v(:,2)/N * a;
        end
        %管控情景
        I_ctrl_all=cell(length(u_list_plot),1);
        for i=1:length(u_list_plot)
            u=u_list_plot(i);
            beta_c=beta * (1-u);
            [~,y_c]=ode45(@(t,y) sir_ode(t,y,beta_c,gamma),t_plot,[N-I0_used,I0_used,0]);
            I_ctrl_all{i}=y_c(:,2)/N * a;
        end
        %组合情景
        v_combo_list=[0.1,0.2,0.4];
        u_combo_list=[0.1,0.2,0.4];
        colors_combo=lines(9);
        legend_entries_combo=cell(1,10);
        legend_entries_combo{1}='基线';
        I_combo_all=cell(9,1);
        idx=1;
        for vc=v_combo_list
            for uc=u_combo_list
                S0_combo=N * (1-vc*eff);
                beta_combo=beta * (1-uc);
                y0_combo=[S0_combo,I0_used,N-S0_combo-I0_used];
                [~,y_combo]=ode45(@(t,y) sir_ode(t,y,beta_combo,gamma),t_plot,y0_combo);
                I_combo_all{idx}=y_combo(:,2)/N * a;
                legend_entries_combo{idx+1}=sprintf('疫苗%d%% 管控%d%%',round(vc*100),round(uc*100));
                idx=idx+1;
            end
        end
        %总图6合1
        fig_combo=figure('Position',[100,100,1400,900],'Visible','on');
        sgtitle(sprintf('%s-%s 详细分析',waves(w).name,regions{r}));
        %子图1：观测与拟合
        subplot(2,3,1);
        plot(t_plot,I_obs,'bo','MarkerSize',5,'LineWidth',1.2);hold on;
        plot(t_plot,I_fit,'r-','LineWidth',2);
        xlabel('时间（周）');ylabel('I_{obs}');
        title('观测 vs 拟合');
        legend('观测','拟合','Location','best');
        grid on;
        %子图2：残差
        subplot(2,3,2);
        stem(t_plot,residuals,'filled','LineWidth',1);
        xlabel('时间（周）');ylabel('残差');
        title('残差分布');
        yline(0,'k--');
        grid on;
        %子图3：残差QQ图
        subplot(2,3,3);
        qqplot(residuals);
        title('残差QQ图');
        grid on;
        %子图4：疫苗情景
        subplot(2,3,4);
        plot(t_plot,I_base,'k-','LineWidth',2);hold on;
        for i=1:length(v_list_plot)
            plot(t_plot,I_vax_all{i},'--','Color',colors(i,:),'LineWidth',1.5);
        end
        xlabel('时间（周）');ylabel('I_{obs}');
        title('疫苗情景（覆盖率）');
        legend_entries_vax=[{'基线'},arrayfun(@(x) sprintf('%d%%',round(x*100)),v_list_plot,'UniformOutput',false)];
        legend(legend_entries_vax,'Location','best');
        grid on;
        %子图5：管控情景
        subplot(2,3,5);
        plot(t_plot,I_base,'k-','LineWidth',2);hold on;
        for i=1:length(u_list_plot)
            plot(t_plot,I_ctrl_all{i},'--','Color',colors(i,:),'LineWidth',1.5);
        end
        xlabel('时间（周）');ylabel('I_{obs}');
        title('管控情景（强度）');
        legend_entries_ctrl=[{'基线'},arrayfun(@(x) sprintf('%d%%',round(x*100)),u_list_plot,'UniformOutput',false)];
        legend(legend_entries_ctrl,'Location','best');
        grid on;
        %子图6：参数+解读+方程（三合一）
        subplot(2,3,6);
        axis off;
        text(0.02,0.92,sprintf('β=%.4f [%.4f, %.4f]',params(1),results(w,r).beta_ci(1),results(w,r).beta_ci(2)),'FontSize',10);
        text(0.02,0.84,sprintf('γ=%.4f [%.4f, %.4f]',params(2),results(w,r).gamma_ci(1),results(w,r).gamma_ci(2)),'FontSize',10);
        text(0.02,0.76,sprintf('R₀=%.4f [%.4f, %.4f]',results(w,r).R0,results(w,r).R0_ci(1),results(w,r).R0_ci(2)),'FontSize',10);
        text(0.02,0.68,sprintf('a=%.4f',params(3)),'FontSize',10);
        text(0.02,0.60,sprintf('R²=%.4f',results(w,r).R2),'FontSize',10);
        text(0.02,0.52,sprintf('RMSE=%.4f',results(w,r).RMSE),'FontSize',10);
        text(0.02,0.44,sprintf('MAE=%.4f',results(w,r).MAE),'FontSize',10);
        text(0.02,0.36,sprintf('MAPE=%.2f%%',results(w,r).MAPE),'FontSize',10);
        text(0.02,0.26,sprintf('平均感染周期=1/γ=%.2f 周',1/params(2)),'FontSize',10);
        text(0.02,0.16,'注：观测值接近0时，MAPE可能偏大，应结合RMSE和MAE判断。',...
            'FontSize',9,'Color','red');
        eqn=sprintf(['SIR方程：\n'...
                       'dS/dt=-%.4f·S·I/N\n'...
                       'dI/dt=%.4f·S·I/N-%.4f·I\n'...
                       'dR/dt=%.4f·I'],...
                       beta,beta,gamma,gamma);
        text(0.52,0.55,eqn,'FontSize',10,'FontName','Monospaced');
        title('参数、解读与模型方程');
        %保存总图
        combo_filename=fullfile(folder_name,'组合图.png');
        exportgraphics(fig_combo,combo_filename,'Resolution',600);
        %单图输出
        %观测与拟合
        fig1=figure('Visible','on');
        plot(t_plot,I_obs,'bo','MarkerSize',5,'LineWidth',1.2);hold on;
        plot(t_plot,I_fit,'r-','LineWidth',2);
        xlabel('时间（周）');ylabel('I_{obs}');
        title(sprintf('%s-%s 观测 vs 拟合',waves(w).name,regions{r}));
        legend('观测','拟合','Location','best');
        grid on;
        exportgraphics(fig1,fullfile(folder_name,'01_观测vs拟合.png'),'Resolution',600);
        close(fig1);
        %残差分布
        fig2=figure('Visible','on');
        stem(t_plot,residuals,'filled','LineWidth',1);
        xlabel('时间（周）');ylabel('残差');
        title(sprintf('%s-%s 残差分布',waves(w).name,regions{r}));
        yline(0,'k--');
        grid on;
        exportgraphics(fig2,fullfile(folder_name,'02_残差分布.png'),'Resolution',600);
        close(fig2);
        %QQ图
        fig3=figure('Visible','on');
        qqplot(residuals);
        title(sprintf('%s-%s 残差QQ图',waves(w).name,regions{r}));
        grid on;
        exportgraphics(fig3,fullfile(folder_name,'03_残差QQ图.png'),'Resolution',600);
        close(fig3);
        %疫苗情景
        fig4=figure('Visible','on');
        plot(t_plot,I_base,'k-','LineWidth',2);hold on;
        for i=1:length(v_list_plot)
            plot(t_plot,I_vax_all{i},'--','Color',colors(i,:),'LineWidth',1.5);
        end
        xlabel('时间（周）');ylabel('I_{obs}');
        title(sprintf('%s-%s 疫苗情景',waves(w).name,regions{r}));
        legend(legend_entries_vax,'Location','best');
        grid on;
        exportgraphics(fig4,fullfile(folder_name,'04_疫苗情景.png'),'Resolution',600);
        close(fig4);
        %管控情景
        fig5=figure('Visible','on');
        plot(t_plot,I_base,'k-','LineWidth',2);hold on;
        for i=1:length(u_list_plot)
            plot(t_plot,I_ctrl_all{i},'--','Color',colors(i,:),'LineWidth',1.5);
        end
        xlabel('时间（周）');ylabel('I_{obs}');
        title(sprintf('%s-%s 管控情景',waves(w).name,regions{r}));
        legend(legend_entries_ctrl,'Location','best');
        grid on;
        exportgraphics(fig5,fullfile(folder_name,'05_管控情景.png'),'Resolution',600);
        close(fig5);
        %组合情景（9种）
        fig6=figure('Visible','on','Position',[100,100,1200,700]);
        plot(t_plot,I_base,'k-','LineWidth',2);hold on;
        for i=1:9
            plot(t_plot,I_combo_all{i},'--','Color',colors_combo(i,:),'LineWidth',1.4);
        end
        xlabel('时间（周）');ylabel('I_{obs}');
        title(sprintf('%s-%s 组合情景（9种疫苗×管控组合）',waves(w).name,regions{r}));
        legend(legend_entries_combo,'Location','eastoutside','FontSize',8);
        grid on;
        exportgraphics(fig6,fullfile(folder_name,'06_组合情景.png'),'Resolution',600);
        close(fig6);
        %参数+解读+方程（三合一）
        fig7=figure('Visible','on','Position',[100,100,1100,700]);
        axis off;
        text(0.05,0.90,sprintf('β=%.4f [%.4f, %.4f]',params(1),results(w,r).beta_ci(1),results(w,r).beta_ci(2)),'FontSize',12);
        text(0.05,0.82,sprintf('γ=%.4f [%.4f, %.4f]',params(2),results(w,r).gamma_ci(1),results(w,r).gamma_ci(2)),'FontSize',12);
        text(0.05,0.74,sprintf('R₀=%.4f [%.4f, %.4f]',results(w,r).R0,results(w,r).R0_ci(1),results(w,r).R0_ci(2)),'FontSize',12);
        text(0.05,0.66,sprintf('a=%.4f',params(3)),'FontSize',12);
        text(0.05,0.58,sprintf('R²=%.4f',results(w,r).R2),'FontSize',12);
        text(0.05,0.50,sprintf('RMSE=%.4f',results(w,r).RMSE),'FontSize',12);
        text(0.05,0.42,sprintf('MAE=%.4f',results(w,r).MAE),'FontSize',12);
        text(0.05,0.34,sprintf('MAPE=%.2f%%',results(w,r).MAPE),'FontSize',12);
        text(0.05,0.22,sprintf('平均感染周期=1/γ=%.2f 周',1/params(2)),'FontSize',12);
        text(0.05,0.12,'注：观测值接近0时，MAPE可能偏大，应结合RMSE和MAE判断。',...
            'FontSize',11,'Color','red');
        eqn=sprintf(['SIR方程：\n'...
                       'dS/dt=-%.4f·S·I/N\n'...
                       'dI/dt=%.4f·S·I/N-%.4f·I\n'...
                       'dR/dt=%.4f·I'],...
                       beta,beta,gamma,gamma);
        text(0.55,0.65,eqn,'FontSize',13,'FontName','Monospaced');
        title(sprintf('%s-%s 参数、解读与方程',waves(w).name,regions{r}));
        exportgraphics(fig7,fullfile(folder_name,'07_参数解读方程.png'),'Resolution',600);
        close(fig7);
    end
end
%总览对比图（保存到"总览图"文件夹）
%图1：四个模型的拟合曲线对比
fig_over1=figure('Position',[100,100,1400,800]);
for w=1:length(waves)
    for r=1:length(regions)
        subplot(length(waves),length(regions),(w-1)*length(regions)+r);
        plot(results(w,r).t,results(w,r).I_obs,'bo','MarkerSize',3);hold on;
        plot(results(w,r).t,results(w,r).I_fit,'r-','LineWidth',2);
        xlabel('时间（周）');ylabel('I_{obs}');
        title(sprintf('%s-%s',waves(w).name,regions{r}));
        legend('观测','拟合','Location','best');
        grid on;
    end
end
sgtitle('四个模型的观测与拟合曲线对比');
exportgraphics(fig_over1,'总览图/拟合曲线对比总览.png','Resolution',600);
close(fig_over1);
%图2：R₀条形图
fig_over2=figure;
bar_data=zeros(length(waves)*length(regions),1);
labels={};
idx=1;
for w=1:length(waves)
    for r=1:length(regions)
        bar_data(idx)=results(w,r).R0;
        labels{idx}=sprintf('%s\n%s',waves(w).name,regions{r});
        idx=idx+1;
    end
end
bar(bar_data);
set(gca,'XTickLabel',labels,'XTickLabelRotation',45);
ylabel('基本再生数 R₀');
title('各模型R₀对比');
grid on;
exportgraphics(fig_over2,'总览图/R0对比条形图.png','Resolution',600);
close(fig_over2);
%图3：疫苗干预效果对比（峰值下降百分比，选择20%、40%为例）
fig_over3=figure;
v_list_plot=[10,20,40];
peak_reduction_vax=zeros(length(waves)*length(regions),length(v_list_plot));
idx=1;
for w=1:length(waves)
    for r=1:length(regions)
        base_peak=results(w,r).vax_results(1,2);
        for i=1:length(v_list_plot)
            peak=results(w,r).vax_results(i+1,2);
            peak_reduction_vax(idx,i)=(base_peak-peak)/base_peak * 100;
        end
        idx=idx+1;
    end
end
bar(peak_reduction_vax);
set(gca,'XTickLabel',labels,'XTickLabelRotation',45);
ylabel('峰值下降百分比 (%)');
title('不同疫苗覆盖率下的峰值下降效果');
legend(arrayfun(@(x) sprintf('%d%%覆盖率',x),v_list_plot,'UniformOutput',false),'Location','best');
grid on;
exportgraphics(fig_over3,'总览图/疫苗效果对比.png','Resolution',600);
close(fig_over3);
%图4：管控干预效果对比（峰值下降百分比）
fig_over4=figure;
u_list_plot=[10,20,40];
peak_reduction_ctrl=zeros(length(waves)*length(regions),length(u_list_plot));
idx=1;
for w=1:length(waves)
    for r=1:length(regions)
        base_peak=results(w,r).control_results(1,2);
        for i=1:length(u_list_plot)
            peak=results(w,r).control_results(i+1,2);
            peak_reduction_ctrl(idx,i)=(base_peak-peak)/base_peak * 100;
        end
        idx=idx+1;
    end
end
bar(peak_reduction_ctrl);
set(gca,'XTickLabel',labels,'XTickLabelRotation',45);
ylabel('峰值下降百分比 (%)');
title('不同管控强度下的峰值下降效果');
legend(arrayfun(@(x) sprintf('%d%%强度',x),u_list_plot,'UniformOutput',false),'Location','best');
grid on;
exportgraphics(fig_over4,'总览图/管控效果对比.png','Resolution',600);
close(fig_over4);
fprintf('\n所有图形和结果已生成。图片已分类保存在各模型文件夹和"总览图"文件夹中，表格已导出为Excel文件。\n');
fprintf('图形窗口保持打开，方便审阅。\n');