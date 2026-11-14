@echo off
rem cleanroom-kit 启动器（Windows）。无需安装，直接调用。
setlocal
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY (
    where python3 >nul 2>nul && set "PY=python3"
)
if not defined PY (
    echo 未找到 Python 解释器（python / python3^)，请先安装 Python 3。
    exit /b 1
)
"%PY%" -m crkit %*
if errorlevel 1 exit /b %errorlevel%
