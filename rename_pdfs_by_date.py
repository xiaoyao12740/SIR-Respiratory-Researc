import pdfplumber
import re
from datetime import datetime,timedelta
from pathlib import Path
import shutil
def week_of_year(date):
    #返回日期所在的年份和周次（ISO周历，周一为一周开始）#
    year,week,_=date.isocalendar()
    return year,week
def extract_date_range(text):
    #从文本中提取起止日期，返回 (start_date, end_date)
    #支持多种分隔符：-、—、－、空格等  
    #尝试多种分隔符：短横线、长破折号、全角破折号，以及可能的空格
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
            elif len(groups)==5:
                #结束年份与开始年份相同
                y1,m1,d1,m2,d2=map(int,groups)
                start=datetime(y1,m1,d1)
                end=datetime(y1,m2,d2)
            else:
                continue
            return start,end
    return None,None
def process_pdf(pdf_path):
    #处理单个PDF，返回期望的文件名 (year_Www.pdf) 或 None#
    try:
        with pdfplumber.open(pdf_path) as pdf:
            #尝试前三页，因为第一页可能只是封面，日期可能在第二或第三页
            for page_num in range(min(3,len(pdf.pages))):
                page=pdf.pages[page_num]
                text=page.extract_text()
                if not text:
                    continue
                print(f"  调试：{pdf_path.name} 第{page_num+1}页部分文本: {text[:200]}...")#打印前200字符
                start,end=extract_date_range(text)
                if start and end:
                    #取结束日期所在的周次（通常报告涵盖一整周）
                    year,week=week_of_year(end)
                    print(f"  提取到日期: {start.date()} 至 {end.date()}, 周次={year}年第{week}周")
                    return f"{year}_W{week:02d}.pdf"
            return None
    except Exception as e:
        print(f"  读取 {pdf_path.name} 出错: {e}")
        return None
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
    #输出报告
    print("\n" + "="*60)
    print("文件名检查报告")
    print("="*60)
    for orig,exp,status in rename_log:
        if status=="正确":
            print(f" {orig} -> 正确")
        elif status=="需重命名":
            print(f" {orig} -> 应改为 {exp}")
        else:
            print(f"? {orig} -> {status}")
    #询问是否执行重命名
    if any(status=="需重命名" for _,_,status in rename_log):
        answer=input("\n是否执行重命名操作？(y/n): ").strip().lower()
        if answer=='y':
            for orig,exp,status in rename_log:
                if status=="需重命名":
                    src=folder_path / orig
                    dst=folder_path / exp
                    if dst.exists():
                        print(f"  警告：目标文件 {exp} 已存在，跳过 {orig}")
                    else:
                        shutil.move(str(src),str(dst))
                        print(f"  已重命名: {orig} -> {exp}")
            print("重命名完成。")
        else:
            print("未执行重命名。")
    else:
        print("\n所有文件名均正确，无需修改。")
if __name__=="__main__":
    main()