@echo off
setlocal
cd /d "%~dp0"
title Upload release to GitHub
if not exist "release\update.json" (
  echo [ERROR] release\update.json not found. Run build_all.bat first.
  pause & exit /b 1
)
where git >nul 2>nul
if errorlevel 1 (
  echo Git not found. Installing Git via winget ...
  winget install --id Git.Git -e --source winget
  echo Close this window and run UploadRelease.bat again.
  pause & exit /b 1
)
set REPO=https://github.com/Minos117/tp.git
set WORK=%TEMP%\zaia_upload
if exist "%WORK%" rmdir /s /q "%WORK%"
echo Cloning %REPO% ...
git clone --depth 1 "%REPO%" "%WORK%"
if errorlevel 1 ( echo [ERROR] clone failed & pause & exit /b 1 )
if exist "%WORK%\files" rmdir /s /q "%WORK%\files"
xcopy /e /i /y /q "release\files" "%WORK%\files" >nul
copy /y "release\update.json" "%WORK%\update.json" >nul
cd /d "%WORK%"
git add -A
git commit -m "Release files + update.json"
echo.
echo Pushing. A GitHub sign-in window may appear (sign in as the repo owner).
git push origin main
if errorlevel 1 ( echo [ERROR] push failed - check sign-in/permission & pause & exit /b 1 )
echo.
echo DONE. Check: https://raw.githubusercontent.com/Minos117/tp/main/update.json
pause
