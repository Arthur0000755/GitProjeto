@echo off
rem AG Vexa Toolkit - confere a copia deste HD (somente leitura).
rem A politica de execucao "Bypass" vale apenas para esta janela.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0AGVexa\Verificar-Copia.ps1" -Raiz "%~dp0."
echo.
pause
