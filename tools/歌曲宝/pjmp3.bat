@echo off
chcp 65001 >nul
title pjmp3.com

python "%~dp0pjmp3_search.py" --interactive

pause
