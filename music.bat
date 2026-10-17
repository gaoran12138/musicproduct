@echo off
setlocal
rem music.bat - launcher for music.py (ASCII only, CRLF, no chinese comments)
set "PY=D:\musicProduct\tools\python310\python.exe"
if not exist "%PY%" (
  echo [XX] python310 not found: %PY%
  exit /b 1
)
set "PYTHONIOENCODING=utf-8"
if not exist "D:\musicProduct\tools\ffmpeg\bin" echo [!!] tools\ffmpeg\bin missing
if not exist "D:\musicProduct\tools\cuda\bin" echo [!!] tools\cuda\bin missing
"%PY%" "D:\musicProduct\music.py" %*
