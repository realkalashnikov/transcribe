@echo off
setlocal
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

:: 3. Menu de inicializacao
echo Escolha o modo de execucao:
echo.
echo   [1] Local Pessoal (Apenas neste computador - Padrao)
echo   [2] Compartilhado / Celular (Tunel Cloudflare HTTPS com PIN)
echo   [3] Instancia Publica Aberta (Estilo Cobalt, historico efemero)
echo   [4] Sair
echo.
set /p opt="Digite a opcao desejada [1-4] (Padrao: 1): "

if "%opt%"=="2" (
    echo.
    echo [MODO] Iniciando com Acesso Remoto seguro para celular...
    python run.py --share
) else if "%opt%"=="3" (
    echo.
    echo [MODO] Iniciando como Instancia Publica aberta ao mundo...
    python run.py --public
) else if "%opt%"=="4" (
    exit /b 0
) else (
    echo.
    echo [MODO] Iniciando localmente em http://localhost:8000 ...
    python run.py
)

pause
