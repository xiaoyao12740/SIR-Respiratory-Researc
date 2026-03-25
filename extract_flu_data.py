import pdfplumber
import pandas as pd
import re
import os
from pathlib import Path
def extract_ili_by_line(text,region):
    #按行提取：在包含关键字的行中搜索百分数
    #返回浮点数或None
    lines=text.split('\n')
    for idx,line in enumerate(lines):
        if f'{region}省份哨点医院报告的' in line:
            match=re.search(r'([\d.]+)%',line)
            if match:
                val=float(match.group(1))
                print(f"      按行提取成功：{region} ILI%={val}")
                return val
    return None
def extract_ili_cross_line(text,region):
    #跨行提取：将文本展平后搜索，处理换行情况
    text_flat=text.replace('\n',' ')
    pattern=rf'{region}省份哨点医院报告的\s*I\s*L\s*I\s*%?\s*为\s*([\d.]+)%'
    match=re.search(pattern,text_flat)
    if match:
        val=float(match.group(1))
        print(f"      跨行提取成功：{region} ILI%={val} (展平后匹配)")
        return val
    return None
def extract_ili_aggressive(text,region):
    #激进提取：在整页文本中搜索关键字后第一个百分数
    keyword=f'{region}省份哨点医院报告的'
    pos=text.find(keyword)
    if pos ==-1:
        return None
    snippet=text[pos:pos + 200]
    match=re.search(r'([\d.]+)%',snippet)
    if match:
        val=float(match.group(1))
        print(f"      激进提取成功：{region} ILI%={val} (在关键字后200字符内)")
        return val
    return None
def extract_number_from_cell(cell):
    #从单元格字符串中提取第一个连续数字（整数），去除千位分隔符
    #返回整数或None
    if cell is None:
        return None
    s=str(cell).strip()
    if not s:
        return None
    #去除逗号（千位分隔符）
    s=s.replace(',','')
    #提取第一个连续数字
    match=re.search(r'\d+',s)
    if match:
        return int(match.group())
    return None
def parse_positive_data(df,pdf_name):
    #从表格中解析检测数和阳性数，返回字典
    #改进：使用 extract_number_from_cell 提取数字，适应多种格式
    data={'south_tests':None,'south_pos':None,'north_tests':None,'north_pos':None}
    for i,row in df.iterrows():
        #将行内容转为字符串用于判断
        row_str=' '.join([str(cell) for cell in row if cell]).lower()
        if '检测数' in row_str:
            #取南方和北方单元格的数字
            south_num=extract_number_from_cell(row[1]) if len(row)>1 else None
            north_num=extract_number_from_cell(row[2]) if len(row)>2 else None
            data['south_tests']=south_num
            data['north_tests']=north_num
            print(f"      检测数 -> 南方: {south_num}, 北方: {north_num}")
        if '阳性数' in row_str and '%' in row_str:
            south_num=extract_number_from_cell(row[1]) if len(row)>1 else None
            north_num=extract_number_from_cell(row[2]) if len(row)>2 else None
            data['south_pos']=south_num
            data['north_pos']=north_num
            print(f"      阳性数 -> 南方: {south_num}, 北方: {north_num}")
    return data
def process_pdf(pdf_path):
    # 处理单个PDF，返回数据字典（包含年份、周次及所有提取值）
    result={
        'year':None, 
        'week':None,
        'south_ili':None,
        'north_ili':None,
        'south_tests':None,
        'south_pos':None,
        'north_tests':None,
        'north_pos':None,
    }
    #从文件名解析年份和周次（格式：YYYY_Www.pdf）
    filename=os.path.basename(pdf_path)
    match=re.search(r'(\d{4})_W(\d+)',filename)
    if match:
        year=int(match.group(1))
        week=int(match.group(2))
        result['year']=year
        result['week']=week
        print(f"\n正在处理: {filename} (年份={year}, 周次={week})")
    else:
        print(f"\n警告：文件名格式无法解析，跳过：{filename}")
        return None

    with pdfplumber.open(pdf_path) as pdf:
        #==========提取 ILI% ==========
        print("   开始提取 ILI%...")
        for page_num,page in enumerate(pdf.pages,start=1):
            text=page.extract_text()
            if not text:
                continue
            if '哨点医院报告的' not in text:
                continue
            print(f"   第{page_num}页包含关键字，尝试提取...")

            #尝试按行提取
            if result['south_ili'] is None:
                south_val=extract_ili_by_line(text,'南方')
                if south_val is not None:
                    result['south_ili']=south_val
            if result['north_ili'] is None:
                north_val=extract_ili_by_line(text,'北方')
                if north_val is not None:
                    result['north_ili']=north_val
            #如果按行失败，尝试跨行提取
            if result['south_ili'] is None:
                south_val=extract_ili_cross_line(text,'南方')
                if south_val is not None:
                    result['south_ili']=south_val
            if result['north_ili'] is None:
                north_val=extract_ili_cross_line(text,'北方')
                if north_val is not None:
                    result['north_ili']=north_val
            #如果南方和北方都已提取，提前结束
            if result['south_ili'] is not None and result['north_ili'] is not None:
                print("   南方和北方 ILI% 均已提取完毕")
                break
        #如果仍有缺失，用激进提取法在剩余页面尝试
        if result['south_ili'] is None or result['north_ili'] is None:
            print("   常规方法存在缺失，尝试激进提取...")
            for page in pdf.pages:
                text=page.extract_text()
                if not text:
                    continue
                if result['south_ili'] is None:
                    south_val=extract_ili_aggressive(text,'南方')
                    if south_val is not None:
                        result['south_ili']=south_val
                if result['north_ili'] is None:
                    north_val=extract_ili_aggressive(text,'北方')
                    if north_val is not None:
                        result['north_ili']=north_val
                if result['south_ili'] is not None and result['north_ili'] is not None:
                    break
        print("   开始提取表格数据（检测数/阳性数）...")
        if len(pdf.pages)>3:
            page4=pdf.pages[3]
            tables=page4.extract_tables()
            if tables:
                df=pd.DataFrame(tables[0])
                table_data=parse_positive_data(df,filename)
                result.update(table_data)
            else:
                print("   第4页未找到表格")
        else:
            print("   PDF不足4页，无法提取表格")
    print(
        f"   第{result['year']}年第{result['week']}周提取结果：南方ILI%={result['south_ili']}, 北方ILI%={result['north_ili']}, "
        f"南方检测={result['south_tests']}, 南方阳性={result['south_pos']}, "
        f"北方检测={result['north_tests']}, 北方阳性={result['north_pos']}")
    return result
def main():
    #设置存放PDF的文件夹路径（请修改为你的实际路径）
    pdf_folder=r'D:\360MoveData\Users\11142\Desktop\24-25周报' #存放所有年份周报的文件夹
    output_csv='周报原始数据表.csv'
    all_data=[]
    pdf_files=sorted(Path(pdf_folder).glob('*.pdf'))
    print("="*60)
    print("开始批量提取流感周报数据（多年份支持）")
    print("="*60)
    #第一阶段：常规提取
    for pdf_file in pdf_files:
        data=process_pdf(str(pdf_file))
        if data is not None: #确保解析成功
            all_data.append(data)
    if not all_data:
        print("未提取到任何数据，请检查文件名格式是否为 YYYY_Www.pdf")
        return
    #转换为DataFrame并按年份、周次排序
    df=pd.DataFrame(all_data)
    df=df.sort_values(['year','week']).reset_index(drop=True)
    #第二阶段：二次补录缺失值
    missing_mask=df['south_ili'].isna() | df['north_ili'].isna()
    missing_indices=df.index[missing_mask].tolist()
    if missing_indices:
        print("\n" + "="*60)
        print("发现缺失值，启动二次补录")
        print("="*60)
        for idx in missing_indices:
            year=df.loc[idx,'year']
            week=df.loc[idx,'week']
            #找到对应PDF文件
            target_filename=f"{year}_W{week:02d}.pdf"
            pdf_file=next((f for f in pdf_files if f.name ==target_filename),None)
            if not pdf_file:
                continue
            print(f"\n重新处理 {target_filename}（补录）...")
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    text=page.extract_text()
                    if not text:
                        continue
                    #补录南方
                    if pd.isna(df.loc[idx,'south_ili']):
                        south_val=extract_ili_aggressive(text,'南方')
                        if south_val is not None:
                            df.loc[idx,'south_ili']=south_val
                            print(f"      补录成功：南方 ILI%={south_val}")
                    #补录北方
                    if pd.isna(df.loc[idx,'north_ili']):
                        north_val=extract_ili_aggressive(text,'北方')
                        if north_val is not None:
                            df.loc[idx,'north_ili']=north_val
                            print(f"      补录成功：北方 ILI%={north_val}")
                    #如果两个都补录完，退出页面循环
                    if not pd.isna(df.loc[idx,'south_ili']) and not pd.isna(df.loc[idx,'north_ili']):
                        break
    else:
        print("\n所有周次数据完整，无需补录")
    #保存最终数据
    df.to_csv(output_csv,index=False,encoding='utf-8-sig')
    print("\n" + "="*60)
    print(f"最终数据已保存至 {output_csv}")
    print("="*60)
    #显示前10行预览
    print("\n提取结果预览（前10行）：")
    print(df.head(10).to_string())
    #缺失值统计
    print("\n缺失值统计：")
    missing_count=df[['south_ili','north_ili']].isna().sum()
    print(f"南方 ILI% 缺失数: {missing_count['south_ili']}")
    print(f"北方 ILI% 缺失数: {missing_count['north_ili']}")
    if missing_count.sum() ==0:
        print("数据完整，无缺失。")
if __name__ =='__main__':
    main()