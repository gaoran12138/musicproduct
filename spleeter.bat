@echo off
rem Spleeter launcher (GPU) - ASCII only, CFRL, GBK-safe
rem Usage: spleeter.bat separate <file> -o <outdir> -p spleeter:2stems
setlocal
set "FFMPEG_BIN=D:\musicProduct\tools\ffmpeg\bin"
set "CUDA_BIN=D:\musicProduct\tools\cuda\bin"
set "PYTHON=D:\musicProduct\tools\python310\python.exe"
set "MODEL_PATH=D:\musicProduct\pretrained_models"
set "PATH=%FFMPEG_BIN%;%CUDA_BIN%;%PATH%"
set "PYTHONIOENCODING=utf-8"
"%PYTHON%" -m spleeter %*
