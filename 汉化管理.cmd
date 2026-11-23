@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if exist "dist\crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe" (
  start "" "dist\crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe"
  exit /b
)
start "" "https://github.com/lingjieheti/crisis-in-the-kremlin-cold-war-zh-cn/releases/latest/download/crisis-in-the-kremlin-cold-war-zh-cn-Setup.exe"
