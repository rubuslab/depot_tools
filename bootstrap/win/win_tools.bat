@echo off
:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will determine if python or git binaries need updates. It
:: returns !0 as failure

setlocal

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

:: TODO: Remove support for "legacy" mode once we're committed to bundle.
if exist "%WIN_TOOLS_ROOT_DIR%\.bleeding_edge" (
  set PYTHON_MANIFEST=python_version_bleeding_edge.txt
  set PYTHON_BIN=python27_bin
  set PYTHON_PURGE_BIN=python276_bin
) else (
  set PYTHON_MANIFEST=legacy
  set PYTHON_BIN=python276_bin
  set PYTHON_PURGE_BIN=python27_bin
)

:: If a different installation directory exists, delete "python.bat" to force
:: a full install and "python.bat" reimage. This is necessary since the CIPD
:: and non-CIPD "python.bat" differ.
if exist "%WIN_TOOLS_ROOT_DIR%\%PYTHON_PURGE_BIN%" (
  rd /q /s "%WIN_TOOLS_ROOT_DIR%\%PYTHON_PURGE_BIN%"
  if exist "%WIN_TOOLS_ROOT_DIR%\python.bat" del "%WIN_TOOLS_ROOT_DIR%\python.bat"
)

:: Do we need to install?
if not exist "%WIN_TOOLS_ROOT_DIR%\python.bat" goto :PY27_DO_INSTALL
if not exist "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%" goto :PY27_DO_INSTALL
if not "%PYTHON_MANIFEST%" == "legacy" goto :PY27_DO_INSTALL
goto :PYTHON_POSTCHECK

:PY27_DO_INSTALL
if "%PYTHON_MANIFEST%" == "legacy" (
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
:: As an optimization, call CIPD executable directly if it exists. Otherwise, use
:: "cipd.bat" to bootstrap it. This is normally not great, but since we call "ensure"
:: at every invocation, offers a speed improvement.
set CIPD_EXE=%WIN_TOOLS_ROOT_DIR%\.cipd_client.exe
if not exist "%CIPD_EXE%" set CIPD_EXE=%WIN_TOOLS_ROOT_DIR%\cipd.bat
call "%CIPD_EXE%" ensure -ensure-file "%~dp0%PYTHON_MANIFEST%" -root "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%"
if not exist "%~dp0python.bat" call copy /y "%~dp0python27.new.bat" "%WIN_TOOLS_ROOT_DIR%\python.bat" 1>nul

:PYTHON_POSTINSTALL
:: Create the batch files.
if not exist "%WIN_TOOLS_ROOT_DIR%\pylint.bat" call copy /y "%~dp0pylint.new.bat" "%WIN_TOOLS_ROOT_DIR%\pylint.bat" 1>nul

:PYTHON_POSTCHECK
set ERRORLEVEL=0
goto :GIT_CHECK

:GIT_CHECK
call "%WIN_TOOLS_ROOT_DIR%\python.bat" "%~dp0git_bootstrap.py"

:END
endlocal & (
  set ERRORLEVEL=%ERRORLEVEL%
)
exit /b %ERRORLEVEL%
