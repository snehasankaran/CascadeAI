@echo off
REM Activate Anaconda so OpenSSL DLLs are on PATH, then run whatever args are passed.
call "C:\Program Files\Anaconda3\Scripts\activate.bat" "C:\Program Files\Anaconda3"
if errorlevel 1 exit /b %errorlevel%
%*
