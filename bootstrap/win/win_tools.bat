@echo off
:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will determine if python or git binaries need updates. It
:: returns 123 if the user's shell must restart, otherwise !0 is failure

:: Sadly, we can't use SETLOCAL here otherwise it ERRORLEVEL is not correctly
:: returned.

set CHROME_INFRA_URL=https://storage.googleapis.com/chrome-infra/
:: It used to be %~dp0 but ADODB.Stream may fail to write to this directory if
:: the directory DACL is set to elevated integrity level.
set ZIP_DIR=%TEMP%

:: Get absolute root directory (.js scripts don't handle relative paths well).
pushd %~dp0..\..
set WIN_TOOLS_ROOT_DIR=%CD%
popd

if "%1" == "force" (
  set WIN_TOOLS_FORCE=1
  shift /1
)

if exist "%WIN_TOOLS_ROOT_DIR%\.python_bleeding_edge" (
  set PYTHON_MANIFEST="python_version_bleeding_edge.txt"
  set PYTHON_BIN="python27_bin"
) else (
  set PYTHON_MANIFEST="legacy"
  set PYTHON_BIN="python276_bin"
)

:PYTHON_CHECK
if not exist "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%" goto :PY27_DO_INSTALL
if not exist "%WIN_TOOLS_ROOT_DIR%\python.bat" goto :PY27_DO_INSTALL
if NOT "%PYTHON_MANIFEST%"=="legacy" (
  set /p PYTHON_VERSION=<"%~dp0%PYTHON_MANIFEST%"
  if exist "%WIN_TOOLS_ROOT_DIR%\python.stamp" (
    set /p PYTHON_CURRENT_VERSION=<"%WIN_TOOLS_ROOT_DIR%\python.stamp"
  ) else (
    set PYTHON_CURRENT_VERSION=""
  )
  if NOT "%PYTHON_CURRENT_VERSION%"=="%PYTHON_VERSION%" goto :PY27_DO_INSTALL
)
goto :PYTHON_POSTCHECK

:PY27_DO_INSTALL
if exist "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%\." rd /q /s "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN"
if "%PYTHON_MANIFEST%"=="legacy" (
  goto :PY27_LEGACY_INSTALL
) else (
  goto :PY27_CIPD_INSTALL
)

:PY27_LEGACY_INSTALL
echo Installing python 2.7.6...
:: Cleanup python directory if it was existing.
set PYTHON_URL=%CHROME_INFRA_URL%python276_bin.zip
if exist "%WIN_TOOLS_ROOT_DIR%\python276_bin\." rd /q /s "%WIN_TOOLS_ROOT_DIR%\python276_bin"
if exist "%ZIP_DIR%\python276.zip" del "%ZIP_DIR%\python276.zip"
echo Fetching from %PYTHON_URL%
cscript //nologo //e:jscript "%~dp0get_file.js" %PYTHON_URL% "%ZIP_DIR%\python276_bin.zip"
if errorlevel 1 goto :PYTHON_LEGACY_FAIL
:: Will create python276_bin\...
call copy /y "%~dp0python276.new.bat" "%WIN_TOOLS_ROOT_DIR%\python.bat" 1>nul
cscript //nologo //e:jscript "%~dp0unzip.js" "%ZIP_DIR%\python276_bin.zip" "%WIN_TOOLS_ROOT_DIR%"
del "%ZIP_DIR%\python276_bin.zip"
goto :PYTHON_POSTINSTALL

:PYTHON_LEGACY_FAIL
echo ... Failed to checkout python automatically.
echo You should get the "prebaked" version at %PYTHON_URL%
set ERRORLEVEL=1
goto :END

:PY27_CIPD_INSTALL
echo Installing python %PYTHON_VERSION%...
mkdir "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%"
call "%WIN_TOOLS_ROOT_DIR%\cipd.bat" -ensure-file "%~dp0%PYTHON_MANIFEST%" -root "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%"
call copy /y "%~dp0python27.new.bat" "%WIN_TOOLS_ROOT_DIR%\python.bat" 1>nul
@echo "%PYTHON_VERSION%"> "%WIN_TOOLS_ROOT_DIR%\python.stamp"
goto :PYTHON_POSTINSTALL

:PYTHON_POSTINSTALL
:: Create the batch files.
call copy /y "%~dp0pylint.new.bat" "%WIN_TOOLS_ROOT_DIR%\pylint.bat" 1>nul
goto :PYTHON_POSTCHECK

:PYTHON_POSTCHECK
set ERRORLEVEL=0
goto :GIT_CHECK

:GIT_CHECK
"%WIN_TOOLS_ROOT_DIR%\python.bat" "%~dp0git_bootstrap.py"
goto :END

:returncode
set WIN_TOOLS_ROOT_DIR=
exit /b %ERRORLEVEL%

:END
call :returncode %ERRORLEVEL%
