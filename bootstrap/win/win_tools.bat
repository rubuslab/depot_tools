@echo off
:: Copyright (c) 2012 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: This script will determine if python or git binaries need updates. It
:: returns !0 as failure
::
:: A previous Python may actually be in use when it is run, preventing us
:: from replacing it outright without breaking running code. To
:: accommodate this, and Python cleanup, we handle Python in two stages:
:: 1) Ensure that *some* Python is available on the system.
:: 2) Run a follow-up program to complete installation and clean up any
::    unused Pythons.
::
:: We detect if there is an existing Python by looking for a "python.bat"
:: shim. If it is absent, we will directly install the non-bleeding-edge
:: Python instance.
::
:: The post-processing will regenerate "python.bat" to point to the current
:: Python instance. Any previous Python installations will stick around, but
:: new invocations will use the new instance. Old installations will die
:: off either due to processes terminating or systems restarting. When this
:: happens, they will be cleaned up by the post-processing script.

setlocal

set CHROME_INFRA_URL=https://storage.googleapis.com/chrome-infra/
:: It used to be %~dp0 but ADODB.Stream may fail to write to this directory if
:: the directory DACL is set to elevated integrity level.
set STAGING_DIR=%TEMP%

:: Get absolute root directory (.js scripts don't handle relative paths well).
pushd %~dp0..\..
set WIN_TOOLS_ROOT_DIR=%CD%
popd

:: Extra arguments to pass to our "win_tools.py" script.
set WIN_TOOLS_EXTRA_ARGS=

if "%1" == "force" (
  set WIN_TOOLS_EXTRA_ARGS=%WIN_TOOLS_EXTRA_ARGS% --force
  shift /1
)

:: Determine if we're running a bleeding-edge installation.
set BOOTSTRAP_ROOT=%STAGING_DIR%\python27_bootstrap_bin
if not exist "%WIN_TOOLS_ROOT_DIR%\.bleeding_edge" (
  set IS_BLEEDING_EDGE=false
  set PYTHON_MANIFEST=python_version.txt
) else (
  set IS_BLEEDING_EDGE=true
  set PYTHON_MANIFEST=python_version_bleeding_edge.txt
  set WIN_TOOLS_EXTRA_ARGS=%WIN_TOOLS_EXTRA_ARGS% --bleeding-edge
)

:: Identify our CIPD executable. If the client executable exists, use it
:: directly; otherwise, use "cipd.bat" to bootstrap the client. This
:: optimization is useful because this script can be run frequently, and
:: reduces execution time noticeably.
set CIPD_EXE=%WIN_TOOLS_ROOT_DIR%\.cipd_client.exe
if not exist "%CIPD_EXE%" set CIPD_EXE=%WIN_TOOLS_ROOT_DIR%\cipd.bat
set WIN_TOOLS_EXTRA_ARGS=%WIN_TOOLS_EXTRA_ARGS% --cipd-client "%CIPD_EXE%"

:: If we're not on bleeding edge, we assume that we will be doing a legacy
:: (non-CIPD) installation.
::
:: TODO: This logic will change when we deprecate legacy mode. For now, we
:: assume !bleeding_edge == legacy.
if "%IS_BLEEDING_EDGE%" == "false" goto :PY27_LEGACY_CHECK

:: We are committed to CIPD, and will use "win_tools.py" to perform our Python
:: installation.
set WIN_TOOLS_EXTRA_ARGS=%WIN_TOOLS_EXTRA_ARGS% --python-manifest "%~dp0%PYTHON_MANIFEST%"

:: If we have a bootstrap Python instance installed, we can jump straight to it.
set WIN_TOOLS_PYTHON_BIN=%WIN_TOOLS_ROOT_DIR%\python.bat
if exist "%WIN_TOOLS_PYTHON_BIN%" goto :WIN_TOOLS_PY

:: Install a bootstrap Python installation with CIPD.
call "%CIPD_EXE%" ensure -ensure-file "%~dp0%PYTHON_MANIFEST%" -root "%BOOTSTRAP_ROOT%"
if errorlevel 1 goto :BOOTSTRAP_DONE

set WIN_TOOLS_PYTHON_BIN=%BOOTSTRAP_ROOT%\bin\python.exe
goto :WIN_TOOLS_PY

:: LEGACY Support
::
:: This is a full Python installer. It falls through to "win_tools.py",
:: instructing it to not handle Python installation. This should be removed
:: once we commit to CIPD.
:PY27_LEGACY_CHECK
if not exist "%WIN_TOOLS_ROOT_DIR%\python.bat" goto :PY27_LEGACY_INSTALL
if not exist "%WIN_TOOLS_ROOT_DIR%\%PYTHON_BIN%" goto :PY27_LEGACY_INSTALL
goto :WIN_TOOLS_PY

:PY27_LEGACY_INSTALL
echo Installing python 2.7.6...
:: Cleanup python directory if it was existing.
set PYTHON_URL=%CHROME_INFRA_URL%python276_bin.zip
if exist "%WIN_TOOLS_ROOT_DIR%\python276_bin\." rd /q /s "%WIN_TOOLS_ROOT_DIR%\python276_bin"
if exist "%STAGING_DIR%\python276.zip" del "%STAGING_DIR%\python276.zip"
echo Fetching from %PYTHON_URL%
cscript //nologo //e:jscript "%~dp0get_file.js" %PYTHON_URL% "%STAGING_DIR%\python276_bin.zip"
if errorlevel 1 goto :PYTHON_LEGACY_FAIL
:: Will create python276_bin\...
cscript //nologo //e:jscript "%~dp0unzip.js" "%STAGING_DIR%\python276_bin.zip" "%WIN_TOOLS_ROOT_DIR%"
:: Create the batch files.
call copy /y "%~dp0python276.new.bat" "%WIN_TOOLS_ROOT_DIR%\python.bat" 1>nul
call copy /y "%~dp0pylint.new.bat" "%WIN_TOOLS_ROOT_DIR%\pylint.bat" 1>nul
del "%ZIP_DIR%\python276_bin.zip"
set ERRORLEVEL=0
goto :WIN_TOOLS_PY

:PYTHON_LEGACY_FAIL
echo ... Failed to checkout python automatically.
echo You should get the "prebaked" version at %PYTHON_URL%
set ERRORLEVEL=1
goto :END

:: This executes "win_tools.py" using the WIN_TOOLS_PYTHON_BIN Python
:: interpreter.
:WIN_TOOLS_PY
call "%WIN_TOOLS_PYTHON_BIN%" "%~dp0\win_tools.py" %WIN_TOOLS_EXTRA_ARGS%

:GIT_CHECK
call "%WIN_TOOLS_ROOT_DIR%\python.bat" "%~dp0git_bootstrap.py"

:END
set EXPORT_ERRORLEVEL=%ERRORLEVEL%
if exist "%BOOTSTRAP_ROOT%" rd /q /s "%BOOTSTRAP_ROOT%" > nul

endlocal & (
  set ERRORLEVEL=%EXPORT_ERRORLEVEL%
)
exit /b %ERRORLEVEL%
