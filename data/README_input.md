# EIS 任务输入数据说明

本包是 Agent 的输入（input_data.zip），包含三个原始 CSV，无任何参考答案内容。

## 文件清单

1. `data/exampleData.csv` —— impedance.py 官方示例数据（MIT 许可）
   - 66 行、3 列、**无表头**：frequency (Hz), Re(Z) (Ohm), Im(Z) (Ohm)
   - 第三列即阻抗虚部 Z''（容性点为负，最高频段有 9 个 Z''>0 的感抗点）
   - 来源：https://github.com/ECSHackWeek/impedance.py/blob/master/data/exampleData.csv

2. `data/Cell_1_GEIS_SOC100.csv` —— 碱性电池 GEIS 数据（CC BY 4.0）
   - 5 列带表头：SOC [%], Voltage [V], Frequency [Hz], Re(Ztot) [Ohm], -Im(Ztot) [Ohm]
   - 122 点（同一电池两组扫描，每组 61 点）；SOC=100%，开路电压 ≈1.60 V
   - 第 5 列是 **-Im(Ztot)**：复阻抗虚部 Z'' = -(-Im 列)
   - 来源：https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_1_GEIS.csv

3. `data/Cell_2_GEIS_SOC70.csv` —— 同上（SOC=70%，开路电压 ≈1.39 V）
   - 来源：https://github.com/marzio-barresi/Electrical-Datasets-Alkaline-Batteries/blob/main/GEIS/Cell_2_GEIS.csv

## 常见坑点（务必注意）

- 电池数据第 5 列为 -Im(Ztot)，**不要把该列直接当作 Z''**；Z'' = -(-Im)。
- 三个文件频率均为降序给出（exampleData 为升序），分析前建议按频率升序排列。
- 最高频段存在 Z''>0 的感抗点（导线/夹具电感），拟合与报告需说明处理方式。
- 论文：Barresi et al., J. Energy Storage 2026, 152: 120719（数据仓库 CC BY 4.0）。
- 输入文件的 SHA256 见打包方提供的 provenance.json；不得修改原始文件。