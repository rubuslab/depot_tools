@echo off
:: Copyright (c) 2016 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: Set variable from file contents
set /p BUILD=<"%~dp0\cipd_client_version"

:: Set variable from command output (2^> NUL silences errors)
for /f %%a in ('git -C %~dp0 rev-parse HEAD 2^> NUL') do set GITREV=%%a

if "%GITREV%" == "" (
  set CIPD_HTTP_USER_AGENT_PREFIX=depot_tools/???
) else (
  set CIPD_HTTP_USER_AGENT_PREFIX=depot_tools/%GITREV%
)


"%~dp0\.cipd_client.exe" selfupdate -version %BUILD%
"%~dp0\.cipd_client.exe" %*
