@echo off
chcp 65001 >nul
title GequBao

echo.
echo ========================================
echo     GequBao - Music Search & Download
echo ========================================
echo.
echo   [1] gequbao.com      (MP3)
echo   [2] jywav.com        (MP3 + FLAC)
echo   [3] pjmp3.com        (browser download)
echo.
set /p choice="  Select (1/2/3): "

if "%choice%"=="1" (
    python "%~dp0gequbao_search.py" --interactive
) else if "%choice%"=="2" (
    python "%~dp0jywav_search.py" --interactive
) else if "%choice%"=="3" (
    python "%~dp0pjmp3_search.py" --interactive
) else (
    echo Invalid choice
)

pause
