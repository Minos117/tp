@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title ZAIA Prepare Personal - build all
echo ============================================================
echo  ZAIA Prepare Personal : install prerequisites, build, setup
echo ============================================================

rem ---- 1) Python 3.9+ with tkinter
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY ( where python >nul 2>nul && set "PY=python" )
if not defined PY goto :install_python
%PY% -c "import sys,tkinter; sys.exit(0 if sys.version_info>=(3,9) else 1)" >nul 2>nul
if errorlevel 1 goto :install_python
goto :have_python

:install_python
echo [!] Python 3.9+ (with tkinter) not found. Trying winget...
where winget >nul 2>nul
if errorlevel 1 (
  echo [X] winget is not available. Install Python 3.12 from https://www.python.org/downloads/ ^(tick "tcl/tk" and "Add to PATH"^) then run this file again.
  pause & exit /b 1
)
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
echo.
echo [i] Python installed. Please CLOSE this window and run build_all.bat again.
pause & exit /b 0

:have_python
echo [1/6] Python OK: & %PY% --version

rem ---- 2) virtual environment + packages
if not exist ".venv\Scripts\python.exe" (
  echo [2/6] Creating virtual environment...
  %PY% -m venv .venv || goto :fail
)
set "VPY=%~dp0.venv\Scripts\python.exe"
echo [2/6] Installing packages...
"%VPY%" -m pip install --upgrade pip >nul
"%VPY%" -m pip install -r requirements.txt || goto :fail

rem ---- 3) compile check
echo [3/6] Checking source...
"%VPY%" -m compileall -q zaia app.py || goto :fail

rem ---- 4) PyInstaller
echo [4/6] Building exe (PyInstaller)...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
"%VPY%" -m PyInstaller --noconfirm --clean zaia.spec || goto :fail
if not exist "dist\ZAIA Prepare Personal\ZAIA Prepare Personal.exe" goto :fail

rem ---- 5) Inno Setup
call :find_iscc
if defined ISCC goto :have_iscc
echo [5/6] Inno Setup not found. Trying winget...
winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
call :find_iscc
if defined ISCC goto :have_iscc
echo [X] Inno Setup 6 not found. Install it from https://jrsoftware.org/isdl.php then run this file again.
pause & exit /b 1
:have_iscc
echo [5/6] Building setup with Inno Setup...
"%ISCC%" installer.iss || goto :fail

rem ---- 6) update.json (SHA-256)
echo [6/6] Creating release\update.json ...
"%VPY%" MakeRelease.py || goto :fail
"%VPY%" MakePatch.py release\update.json || goto :fail

echo.
echo ============================================================
echo  DONE.  Setup file: %~dp0Output\
echo         Update files: %~dp0release\
echo ============================================================
dir /b Output
pause & exit /b 0

:find_iscc
set "ISCC="
for %%P in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do if exist %%P set "ISCC=%%~P"
exit /b 0

:fail
echo.
echo [X] Build failed. See messages above.
pause & exit /b 1
