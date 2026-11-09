@echo off
rem cleanroom-kit 启动器（Windows）。无需安装，直接调用。
setlocal
set "ROOT=%~dp0.."
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
python -m crkit %*
