@echo off
chcp 65001 >nul 2>&1  :: 永久解决中文乱码问题
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo 周报批量重命名工具
echo 核心规则：按文件修改时间命名，最多命名到第52周，支持续接已有文件
set /p "target_year=请输入要命名的年份（如2024/2025/2026）："
echo.%target_year%|findstr /r "^[0-9][0-9][0-9][0-9]$">nul || (
    echo 错误：年份必须是4位数字！
    pause
    exit /b 1
)
set /p "start_week=请输入起始周数（如从第1周开始则输入1）："
echo.%start_week%|findstr /r "^[0-9][0-9]*$">nul || (
    echo 错误：起始周数必须是数字！
    pause
    exit /b 1
)
if !start_week! lss 1 (
    echo 提示：起始周数不能小于1，已自动修正为1
    set "start_week=1"
)
if !start_week! gtr 52 (
    echo 提示：起始周数不能大于52，已自动修正为52
    set "start_week=52"
)
echo.
echo 请选择文件排序方式（按修改时间）：
echo 1 - 正序（时间早的文件 → 小周数，如W01）
echo 2 - 逆序（时间晚的文件 → 小周数，如W01）
set /p "sort_type=请输入数字1或2："
if not "!sort_type!"=="1" if not "!sort_type!"=="2" (
    echo 错误：只能输入1或2，已默认选择正序（1）
    set "sort_type=1"
)
if !sort_type!==1 (
    set "sort_param=/o:d"
    set "sort_desc=正序（早→晚）"
) else (
    set "sort_param=/o:-d"
    set "sort_desc=逆序（晚→早）"
)
set "max_exist_week=0"
for /f "tokens=3 delims=_." %%n in ('dir /b "!target_year!_W*.pdf" 2^>nul') do (
    set "num=%%n"
    if !num! gtr !max_exist_week! set "max_exist_week=!num!"
)
if !max_exist_week! geq 1 (
    echo.
    echo 检测到文件夹中已有 !target_year!_W01 至 !target_year!_W!max_exist_week! 的文件
    set /p "confirm=是否从第 !max_exist_week!+1=!max_exist_week!+1 周开始续接命名？(输入Y确认，其他键使用你输入的起始周)："
    if /i "!confirm!"=="Y" (
        set "start_week=!max_exist_week!+1"
    )
)
set /a "final_start=!start_week!"
if !final_start! gtr 52 (
    echo 起始周数超过52，无文件可命名！
    pause
    exit /b 1
)
set "current_week=!final_start!"
echo.
echo 开始命名：
echo 年份=!target_year!，起始周=!final_start!，排序方式=!sort_desc!，最多到第52周
echo ---------------------------------------------------------------
set "rename_count=0"
:: 核心：按选择的排序方式处理未命名的PDF文件
for /f "delims=" %%f in ('dir /b /a-d !sort_param! *.pdf ^| findstr /v "!target_year!_W"') do (
    if !current_week! gtr 52 goto rename_end
    set "week_str=0!current_week!"
    set "week_str=!week_str:~-2!"
    ren "%%f" "!target_year!_W!week_str!.pdf"
    set /a rename_count+=1
    echo 成功：[%%f] → [!target_year!_W!week_str!.pdf]
    set /a current_week+=1
)
:rename_end
echo ---------------------------------------------------------------
echo 重命名完成！
echo 本次共成功命名 !rename_count! 个文件
echo 命名范围：!target_year!_W!final_start! 至 !target_year!_W!current_week!-1
pause