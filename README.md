# 流感监测周报数据提取与 SIR 建模分析

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.xxxxxxx.svg)](https://doi.org/10.5281/zenodo.xxxxxxx)  
*（请替换为实际归档后的 DOI 链接）*

## 项目简介

本项目用于处理中国流感监测周报（PDF 格式），自动化提取南北方 **ILI%**、**检测数**、**阳性数** 等关键指标，计算观测感染代理序列 \( I_{obs} \)，并基于 SIR 动力学模型进行参数估计与干预情景模拟（疫苗接种、接触管控及组合策略）。

研究涵盖了 2024–2025 年跨年波和 2025 年末波两个流行阶段，按南北方分区建模，输出传播参数（\( \beta, \gamma, R_0 \)）、模型拟合优度（RMSE, MAE, R²）及不同干预力度下的峰值/累计感染下降幅度。

## 目录结构
├── data/ # 放置原始 PDF 周报（需自行下载）
├── scripts/
│ ├── batch_rename.bat # 批量重命名（按修改时间）
│ ├── rename_pdfs.py # 基于 PDF 日期提取 ISO 周次并重命名
│ ├── extract_flu_data.py # 提取 ILI%、检测数、阳性数 → CSV
│ ├── check_data_quality.py # 数据质量检查（缺失、突变、一致性）
│ ├── preprocess.m # MATLAB 数据预处理（生成 I_obs）
│ ├── mainSIR.m # SIR 模型主程序（拟合 + 干预模拟）
│ ├── sir_ode.m # SIR 微分方程
│ ├── sir_simulate.m # 模型求解及尺度映射
│ └── fit_sir_quiet.m # 静默拟合函数
├── results/ # 运行后自动生成的结果图表及表格
├── requirements.txt # Python 依赖列表
├── LICENSE # 许可证文件（MIT 推荐）
└── README.md

text

## 环境要求

### Python 3.8+
- `pdfplumber` – 解析 PDF 表格与文本
- `pandas` – 数据处理
- `numpy` – 数值计算

安装命令：
pip install pdfplumber pandas numpy
MATLAB R2020b 或更高版本
需要 Optimization Toolbox（lsqcurvefit）

无需额外工具箱

使用流程
1. 准备 PDF 数据
将原始流感周报 PDF 放入 data/ 文件夹，文件名需符合 年份_W周次.pdf 格式（可使用 batch_rename.bat 或 rename_pdfs.py 自动重命名）。

2. 提取数据到 CSV
bash
python scripts/extract_flu_data.py
输出文件：周报原始数据表.csv

3. 质量检查（可选）
bash
python scripts/check_data_quality.py
4. MATLAB 预处理与建模
在 MATLAB 中依次运行：

matlab
preprocess       % 生成 I_obs 并保存 processed_data.mat
mainSIR          % 执行 SIR 拟合与情景模拟
结果将保存在 results/ 文件夹（自动创建），包括：

模型参数对比表（Excel）

情景模拟结果表（Excel）

各波次/区域的拟合曲线、残差图、干预效果图

总览图文件夹（R₀ 条形图、干预效果对比等）

重要参数说明
参数	含义
β
β	有效传播率（每周）
γ
γ	恢复率（每周）
R
0
=
β
/
γ
R 
0
​
 =β/γ	基本再生数
a
a	尺度因子（将模拟感染比例映射至观测 
I
o
b
s
I 
obs
​
 ）
eff
eff	疫苗有效性（默认 0.8）
引用信息
如果您在学术工作中使用本代码，请引用：

作者姓名，论文标题，学位论文，年份。DOI: xx.xxxx/zenodo.xxxxxx

同时建议引用依赖的开源库：pdfplumber, pandas, MATLAB。

许可证
本项目采用 MIT 许可证，详情见 LICENSE 文件。
数据来源于国家流感中心公开周报，仅限学术研究使用。

联系方式
如有问题或建议，请通过 GitHub Issues 联系，或发送邮件至：xiaoyaotongxue8@gmail.com
