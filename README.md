# 流感/呼吸道传染病监测数据分析与 SIR 建模

[![DOI](https://zenodo.org/badge/1191901845.svg)](https://doi.org/10.5281/zenodo.20267603)

本仓库包含与学位论文附录的完整源代码，用于处理中国流感监测周报（PDF），提取南北方 ILI%、检测数、阳性数等关键指标，构建观测感染代理序列 \( I_{obs} \)，并基于 SIR 动力学模型进行参数估计与干预情景模拟（疫苗接种、接触管控及组合策略）。

## 目录结构

建议将原始 PDF 周报放入 `data/` 文件夹，脚本放入 `scripts/`，运行结果将自动生成在 `results/` 中。
├── data/ # 存放原始 PDF 周报（需自行下载）
├── scripts/
│ ├── batch_rename.bat # 批处理：按修改时间批量重命名 PDF
│ ├── rename_pdfs.py # Python：根据 PDF 内日期提取 ISO 周次并重命名
│ ├── extract_flu_data.py # 提取 ILI%、检测数、阳性数 → CSV
│ ├── check_data_quality.py # 数据质量检查（缺失、突变、逻辑一致性）
│ ├── preprocess.m # MATLAB 预处理：计算 I_obs，保存 processed_data.mat
│ ├── mainSIR.m # SIR 模型主程序：拟合 + 干预模拟
│ ├── sir_ode.m # SIR 微分方程
│ ├── sir_simulate.m # 模型求解及尺度映射
│ └── fit_sir_quiet.m # 静默拟合函数
├── results/ # 运行后自动生成的图表、表格（不提前上传）
├── requirements.txt # Python 依赖列表
├── LICENSE # MIT 许可证
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
需要 Optimization Toolbox（提供 lsqcurvefit 函数）

无需其他工具箱

使用流程
1. 准备 PDF 数据
从国家流感中心官网下载监测周报（PDF 格式）

将 PDF 放入 data/ 文件夹

运行 batch_rename.bat 或 rename_pdfs.py 将文件重命名为 年份_W周次.pdf 格式

2. 提取数据到 CSV
bash
cd scripts
python extract_flu_data.py
输出文件：周报原始数据表.csv（保存在当前目录）

3. 质量检查（可选）
bash
python check_data_quality.py
4. MATLAB 预处理与建模
在 MATLAB 中依次运行：

matlab
preprocess       % 生成 I_obs 并保存 processed_data.mat
mainSIR          % 执行 SIR 拟合与情景模拟
结果将自动保存在 results/ 文件夹中，包括：

模型参数对比表.xlsx：各波次、区域的 β, γ, R₀ 及拟合优度

情景模拟结果表.xlsx：疫苗、管控、组合干预的峰值/累计感染下降百分比

各波次/区域的子文件夹：内含拟合曲线、残差分析、干预效果图等

总览图/ 文件夹：R₀ 条形图、干预效果对比总览等

重要参数说明
参数	含义
β
β	有效传播率（每周每个感染者导致的易感者感染概率）
γ
γ	恢复率（每周感染者康复的比例）
R
0
=
β
/
γ
R 
0
​
 =β/γ	基本再生数（完全易感人群中的平均传染人数）
a
a	尺度因子（将模型模拟的感染比例映射到观测指标 
I
o
b
s
I 
obs
​
 ）
eff
eff	疫苗有效性（默认 0.8，即 80%）
引用信息
若您在研究中使用本代码，请引用：

作者姓名，论文标题，学位论文，年份。DOI: 10.5281/zenodo.20267603

同时建议引用依赖的开源工具：pdfplumber, pandas, numpy, MATLAB 及 Optimization Toolbox。

许可证
本项目采用 MIT 许可证，详情见仓库中的 LICENSE 文件。
数据来源于国家流感中心公开周报，仅限学术研究使用。使用本代码产生的结果请遵守相关数据使用协议。

联系方式
如有问题或建议，请在 GitHub 仓库提交 Issue。
