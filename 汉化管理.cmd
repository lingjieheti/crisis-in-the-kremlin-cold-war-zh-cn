@echo off
setlocal
set "PYTHONUTF8=1"
chcp 65001 >nul
pushd "%~dp0" || exit /b 1
where py.exe >nul 2>nul
if errorlevel 1 goto python
py -3.12 -c "import sys" >nul 2>nul
if errorlevel 1 goto latest
py -3.12 -B manage.py
goto finish
:latest
py -3 -B manage.py
goto finish
:python
where python.exe >nul 2>nul
if errorlevel 1 goto missing
python -B manage.py
goto finish
:missing
echo 请先从 python.org 安装 64 位 Python 3.11 或更高版本，再运行汉化管理。
pause
popd
exit /b 1
:finish
set result=%errorlevel%
echo.
pause
popd
exit /b %result%
