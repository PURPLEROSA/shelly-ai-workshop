@echo off
chcp 65001 >nul
title Studio
cd /d "%~dp0"

if not exist "pyproject.toml" (
  echo.
  echo   This file has to stay inside the studio folder.
  echo   If you opened it from inside the ZIP: right-click the ZIP, choose "Extract All",
  echo   then run start.bat from the extracted studio folder.
  echo.
  pause
  exit /b 1
)

set "PATH=%USERPROFILE%\.local\bin;%PATH%"

where uv >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Installing uv, a small tool that sets up Python for the studio...
  echo.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
)

where uv >nul 2>nul
if errorlevel 1 (
  echo   Could not install uv automatically.
  echo   Install it from https://docs.astral.sh/uv/ and run this file again.
  pause
  exit /b 1
)

echo.
echo   Getting the studio ready. The first run downloads its parts and takes a few minutes...
uv sync --no-dev
if errorlevel 1 (
  echo.
  echo   Setup failed. Check the internet connection and run this file again.
  echo   If it keeps failing, take a photo of this window.
  pause
  exit /b 1
)
uv run --no-dev --no-sync python -m app %*
if errorlevel 1 pause
