@echo off
setlocal
chcp 65001 >nul
title Transcribe Studio

echo ========================================================
echo   Transcribe Studio - faster-whisper ^& Cloud APIs
echo ========================================================
echo.

:: 1. Verifica se o Python esta instalado
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] O Python nao foi encontrado no seu computador!
    echo.
    echo Como instalar em 1 minuto:
    echo 1. Baixe em: https://www.python.org/downloads/
    echo 2. ATENCAO: Marque a caixinha "Add python.exe to PATH" ao instalar!
    echo.
    echo Pressione qualquer tecla para abrir a pagina do Python no navegador...
    pause >nul
    start https://www.python.org/downloads/
    exit /b 1
)

:: 2. Verifica se as dependencias estao instaladas
python -c "import fastapi, faster_whisper" >nul 2>nul
if %errorlevel% neq 0 (
    echo [CONFIGURACAO] Instalando dependencias necessarias pela primeira vez...
    echo Isso pode levar alguns segundos, por favor aguarde...
    echo.
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo [ERRO] Falha ao instalar as dependencias. Verifique sua conexao com a internet.
        pause
        exit /b 1
    )
    echo.
    echo [SUCESSO] Dependencias instaladas com sucesso!
    echo.
)

:: 3. Repassa a execucao diretamente para o Python (Menu Interativo Moderno)
python run.py %*
if %errorlevel% neq 0 (
    pause
)
