@echo off
:: Copyright (c) 2016 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: Bootstrap CIPD client if it is not present and run it with user agent
:: variable that corresponds to current revision of depot_tools.
	

set MYPATH=%~dp0

:: /p sets variable from file contents
set /p CIPD_CLIENT_VER=<"%MYPATH%\cipd_client_version"
set    CIPD_CLIENT_BIN=%MYPATH%\.cipd_client.exe

if exist "%CIPD_CLIENT_BIN%" goto :RUN

:: Download client binary
set CIPD_CLIENT_SRV=https://chrome-infra-packages.appspot.com


set PLAT=windows
if defined ProgramFiles(x86) (
  set ARCH=amd64
) else (
  set ARCH=386
)

set URL=%CIPD_CLIENT_SRV%/client?platform=%PLAT%-%ARCH%^&version=%CIPD_CLIENT_VER%

echo Bootstrapping CIPD client for %PLAT%-%ARCH%...
:: enabledelayedexpansion is needed to avoid ampersand processing
setlocal enabledelayedexpansion
echo From !URL!

cscript //nologo //e:jscript "%MYPATH%\bootstrap\win\get_file.js" !URL! "%CIPD_CLIENT_BIN%"
endlocal


:RUN

:: Set variable from command output (2^> NUL silences errors)
for /f %%a in ('git -C %MYPATH% rev-parse HEAD 2^> NUL') do set GITREV=%%a

if "%GITREV%" == "" (
  set CIPD_HTTP_USER_AGENT_PREFIX=depot_tools/???
) else (
  set CIPD_HTTP_USER_AGENT_PREFIX=depot_tools/%GITREV%
)


"%CIPD_CLIENT_BIN%" selfupdate -version %CIPD_CLIENT_VER%
if %ERRORLEVEL%==0 goto :UPTODATE
echo selfupdate failed: run
echo   set CIPD_HTTP_USER_AGENT_PREFIX=%CIPD_HTTP_USER_AGENT_PREFIX%/manual && "%CIPD_CLIENT_BIN%" selfupdate -version %CIPD_CLIENT_VER%
echo to diagnose"
exit 1

:UPTODATE
"%CIPD_CLIENT_BIN%" %*
