@echo off
setlocal
chcp 65001 >nul
title Parar Transcribe Studio

echo ========================================================
echo   Encerrando Transcribe Studio em Segundo Plano
echo ========================================================
echo.

python run.py --stop

echo.
ping 127.0.0.1 -n 3 >nul
exit /b 0
