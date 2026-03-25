import pdfplumber
import re
import os
import shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict
def week_of_year(date):
    #通过PDF内容检查PDF是否命名正确
    year,week,_=date.isocalendar()
    return year,week
def extract_date_range(text):
    #从文本中提取起止日期，返回 (start_date, end_date)
    #支持多种分隔符：-、—、－、空格等
    patterns=[
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*[-—－]\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日',
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*-\s*(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日',
        r'(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日\s*[－-]\s*(\d{1,2})月\s*(\d{1,2})日',#省略结束年份
    ]
    for pattern in patterns:
        match=re.search(pattern,text)
        if match:
            groups=match.groups()
            if len(groups)==6:
                y1,m1,d1,y2,m2,d2=map(int,groups)
                start=datetime(y1,m1,d1)
                end=datetime(y2,m2,d2)
                return start,end
            elif len(groups)==5:
                y1,m1,d1,m2,d2=map(int,groups)
                start=datetime(y1,m1,d1)
                end=datetime(y1,m2,d2)
                return start,end
    return None,None
def process_pdf(pdf_path):
    #处理单个PDF，返回期望的文件名 (year_Www.pdf) 或 None#
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num in range(min(3,len(pdf.pages))):
                page=pdf.pages[page_num]
                text=page.extract_text()
                if not text:
                    continue
                start,end=extract_date_range(text)
                if start and end:
                    year,week=week_of_year(end)
                    return f"{year}_W{week:02d}.pdf"
            return None
    except Exception as e:
        print(f"  读取 {pdf_path.name} 出错: {e}")
        return None
def backup_files(folder_path,backup_dir):
    #备份所有PDF到backup_dir#
    backup_path=folder_path / backup_dir
    backup_path.mkdir(exist_ok=True)
    count=0
    for pdf in folder_path.glob("*.pdf"):
        shutil.copy2(pdf,backup_path / pdf.name)
        count +=1
    print(f"已备份 {count} 个文件到 {backup_path}")
    return backup_path
def main():
    folder=r'D:\360MoveData\Users\11142\Desktop\24-25周报'
    folder_path=Path(folder)
    if not folder_path.exists():
        print("文件夹不存在！")
        return
    pdf_files=sorted(folder_path.glob("*.pdf"))
    if not pdf_files:
        print("未找到PDF文件。")
        return
    print("\n开始分析文件名与内容...\n")
    rename_log=[]#(原文件名, 期望文件名, 状态)
    expected_to_originals=defaultdict(list)#期望文件名 -> 原始文件名列表

    for pdf_file in pdf_files:
        print(f"处理: {pdf_file.name}")
        expected=process_pdf(pdf_file)
        if expected is None:
            rename_log.append((pdf_file.name,"无法解析","跳过"))
            continue
        current=pdf_file.name
        if current==expected:
            rename_log.append((current,expected,"正确"))
        else:
            rename_log.append((current,expected,"需重命名"))

        expected_to_originals[expected].append(current)
    #统计
    total_files=len(pdf_files)
    correct_count=sum(1 for _,_,s in rename_log if s=="正确")
    rename_count=sum(1 for _,_,s in rename_log if s=="需重命名")
    skip_count=sum(1 for _,_,s in rename_log if s=="跳过")
    print("\n" + "="*60)
    print("文件名检查报告")
    print("="*60)
    print(f"总文件数: {total_files}")
    print(f"命名正确: {correct_count}")
    print(f"需要重命名: {rename_count}")
    print(f"无法解析: {skip_count}")
    print("-"*60)
    for orig,exp,status in rename_log:
        if status=="正确":
            print(f" {orig} -> 正确")
        elif status=="需重命名":
            print(f" {orig} -> 应改为 {exp}")
        else:
            print(f"? {orig} -> {status}")
    print("="*60)
    #检测重复目标（多个源对应同一期望）
    duplicates={exp:files for exp,files in expected_to_originals.items() if len(files)>1}
    if duplicates:
        print("\n检测到重复目标（多个文件对应同一个期望文件名）：")
        for exp,files in duplicates.items():
            print(f"   - {exp}: {', '.join(files)}")
        duplicate_count=len(duplicates)
        duplicate_files=sum(len(files) for files in duplicates.values())
        print(f"共 {duplicate_count} 个目标出现重复，涉及 {duplicate_files} 个文件。")
    else:
        print("\n无重复目标文件。")
    #检测缺失周次
    years_present=set()
    for exp in expected_to_originals.keys():
        year=int(exp[:4])
        years_present.add(year)
    if years_present:
        expected_weeks=set()
        for year in years_present:
            for week in range(1,53):
                expected_weeks.add(f"{year}_W{week:02d}.pdf")
        actual_weeks=set(expected_to_originals.keys())
        missing_weeks=expected_weeks - actual_weeks

        if missing_weeks:
            print(f"\n缺失 {len(missing_weeks)} 个周次文件，请下载后放入文件夹：")
            for w in sorted(missing_weeks):
                print(f"   - {w}")
        else:
            print("\n所有周次文件齐全！")
    else:
        print("\n没有成功解析的周次，无法检测缺失。")
    #安全重命名
    if rename_count>0:
        print("\n准备进行安全重命名...")
        backup_answer=input("是否先备份所有文件到 'backup' 文件夹？(y/n): ").strip().lower()
        if backup_answer=='y':
            backup_dir="backup_" + datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path=backup_files(folder_path,backup_dir)
            print("备份完成，可随时从备份恢复。")
        else:
            print("跳过备份，直接进行重命名。")
        #使用临时后缀法重命名
        print("\n开始重命名操作...")
        temp_suffix=".tmp_rename"
        temp_files=[]#(临时路径, 最终目标)
        #第一步：将所有需要重命名的源文件加上临时后缀
        for orig,exp,status in rename_log:
            if status=="需重命名":
                src=folder_path / orig
                if src.exists():
                    temp_dst=src.with_name(src.name + temp_suffix)
                    shutil.move(str(src),str(temp_dst))
                    temp_files.append((temp_dst,exp))
                    print(f"  临时移动: {src.name} -> {temp_dst.name}")
        #第二步：将临时文件重命名为最终目标
        rename_success=0
        rename_fail=0
        for temp_dst,final_name in temp_files:
            final_dst=folder_path / final_name
            if final_dst.exists():
                print(f"  警告：目标文件 {final_name} 已存在，跳过 {temp_dst.name}（请手动检查）")
                rename_fail +=1
            else:
                shutil.move(str(temp_dst),str(final_dst))
                print(f"  重命名: {temp_dst.name} -> {final_name}")
                rename_success +=1

        print(f"重命名完成：成功 {rename_success} 个，失败 {rename_fail} 个。")
        #如果有失败，列出遗留的临时文件
        if rename_fail>0:
            print("\n遗留的临时文件（请手动处理）：")
            for temp_dst,_ in temp_files:
                if temp_dst.exists():
                    print(f"  {temp_dst.name}")
    else:
        print("\n所有文件名已正确，无需重命名。")
    #最终统计
    after_files=list(folder_path.glob("*.pdf"))
    after_count=len(after_files)
    print(f"\n最终文件夹内共有 {after_count} 个PDF文件。")
    if after_count==correct_count + rename_count:#原本需要改名的文件现在都改好了
        print("所有文件已正确命名。")
    else:
        print("请检查最终文件列表。")
    print("\n所有操作完成！")
if __name__=="__main__":
    main()