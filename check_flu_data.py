import pandas as pd
import numpy as np
def check_data_quality(df):
    print("="*60)
    print("流感监测数据质量检查报告")
    print("="*60)
    #检查提取到的csv数值合理性与缺失值
    #1. 缺失值检查
    print("\n1. 缺失值检查：")
    missing=df.isnull().sum()
    if missing.sum()==0:
        print("   无缺失值，数据完整。")
    else:
        for col in missing[missing>0].index:
            print(f"   列 {col} 缺失 {missing[col]} 行")
            rows=df[df[col].isnull()].index.tolist()
            print(f"       缺失行索引: {rows}")
    #2. 重复行检查（完全相同）
    print("\n2. 重复行检查：")
    dup=df[df.duplicated(keep=False)]
    if len(dup)==0:
        print("   无完全重复的行。")
    else:
        print(f"   发现 {len(dup)} 行重复记录：")
        print(dup)
    #3. 连续两行完全相同（仅数值列）
    print("\n3. 连续两行完全相同检查（数值列）：")
    numeric_cols=['south_ili','north_ili','south_tests','south_pos','north_tests','north_pos']
    identical_pairs=[]
    for i in range(len(df)-1):
        if (df.loc[i,numeric_cols]==df.loc[i+1,numeric_cols]).all():
            identical_pairs.append((i,i+1))
    if identical_pairs:
        print(f"   发现 {len(identical_pairs)} 处连续两行完全相同：")
        for pair in identical_pairs:
            print(f"       行 {pair[0]} 与 行 {pair[1]} 完全相同")
    else:
        print("   无连续两行完全相同的情况。")
    #4. 突变检查（相邻周变化绝对值）
    print("\n4. 相邻周突变检查（ILI%变化超过5个百分点）：")
    threshold_ili=5.0
    for col in ['south_ili','north_ili']:
        diff=df[col].diff().abs()
        outliers=diff[diff>threshold_ili]
        if len(outliers)>0:
            print(f"   列 {col} 在以下行存在突变（变化 >{threshold_ili}%）：")
            for idx in outliers.index:
                print(f"       行 {idx}: {df.loc[idx,col]} (与上一行变化 {diff[idx]:.2f})")
        else:
            print(f"   列 {col} 无显著突变。")
    print("\n5. 相邻周突变检查（检测数变化超过2000）：")
    threshold_tests=2000
    for col in ['south_tests','north_tests']:
        diff=df[col].diff().abs()
        outliers=diff[diff>threshold_tests]
        if len(outliers)>0:
            print(f"   列 {col} 在以下行存在突变（变化 >{threshold_tests}）：")
            for idx in outliers.index:
                print(f"       行 {idx}: {df.loc[idx,col]} (与上一行变化 {diff[idx]:.0f})")
        else:
            print(f"   列 {col} 无显著突变。")
    #5. 数值范围检查
    print("\n6. 数值范围检查：")
    #ILI% 应在0-100之间
    for col in ['south_ili','north_ili']:
        out_of_range=df[(df[col] < 0) | (df[col]>100)]
        if len(out_of_range)>0:
            print(f"   列 {col} 存在超出0-100的值：")
            print(out_of_range[['year','week',col]])
        else:
            print(f"   列 {col} 全部在合理范围0-100内。")
    #检测数、阳性数应为非负整数
    for col in ['south_tests','north_tests','south_pos','north_pos']:
        negative=df[df[col] < 0]
        if len(negative)>0:
            print(f"   列 {col} 存在负值：")
            print(negative[['year','week',col]])
        else:
            print(f"   列 {col} 全部为非负值。")
    #6. 阳性数 <=检测数
    print("\n7. 阳性数 ≤ 检测数检查：")
    south_invalid=df[df['south_pos']>df['south_tests']]
    if len(south_invalid)>0:
        print("   南方存在阳性数大于检测数的行：")
        print(south_invalid[['year','week','south_tests','south_pos']])
    else:
        print("   南方所有阳性数 ≤ 检测数。")
    north_invalid=df[df['north_pos']>df['north_tests']]
    if len(north_invalid)>0:
        print("   北方存在阳性数大于检测数的行：")
        print(north_invalid[['year','week','north_tests','north_pos']])
    else:
        print("   北方所有阳性数 ≤ 检测数。")
    #7. 周次顺序完整性（可选项）
    print("\n8. 周次顺序检查（确保每年1-52周连续）：")
    years=df['year'].unique()
    for yr in years:
        weeks=df[df['year']==yr]['week'].values
        expected=set(range(1,53))
        missing=expected - set(weeks)
        if missing:
            print(f"   {yr}年缺失周次: {sorted(missing)}")
        else:
            print(f"   {yr}年周次完整。")
    print("\n" + "="*60)
    print("检查完成。")
    print("="*60)
if __name__=="__main__":
    #读取CSV文件
    file_path="周报原始数据表.csv" #修改为实际路径
    df=pd.read_csv(file_path)
    check_data_quality(df)