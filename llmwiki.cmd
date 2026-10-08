@echo off
rem llmwiki launcher (Windows). Runs tools\llmwiki with this folders .venv Python.
setlocal
set "DIR=%~dp0"
set "PY=%DIR%.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [llmwiki] .venv not found. Run first: powershell -NoProfile -ExecutionPolicy Bypass -File setup\bootstrap-windows.ps1 1>&2
  exit /b 3
)
set "PYTHONPATH=%DIR%tools;%PYTHONPATH%"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if not defined LLMWIKI_ROOT set "LLMWIKI_ROOT=%DIR:~0,-1%"
rem UTF-8 code page while llmwiki runs (Korean/emoji output), then restore the previous one.
set "_LLMWIKI_CP="
for /f "tokens=2 delims=:." %%a in ('chcp') do set "_LLMWIKI_CP=%%a"
chcp 65001 >nul 2>&1
"%PY%" -m llmwiki %*
set "_LLMWIKI_RC=%ERRORLEVEL%"
if defined _LLMWIKI_CP chcp %_LLMWIKI_CP% >nul 2>&1
exit /b %_LLMWIKI_RC%
