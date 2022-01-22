@echo off
rem Copyright (c) 2018 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.
setlocal

rem Shall skip automatic update?
IF "%DEPOT_TOOLS_UPDATE%" == "0" GOTO :CALL_GSUTIL

rem Synchronize the root directory before deferring control back to gsutil.py.
call "%~dp0update_depot_tools.bat" %*
rem Abort the script if we failed to update depot_tools.
IF %errorlevel% NEQ 0 (
  goto :EOF
)

:CALL_GSUTIL
rem Ensure that "depot_tools" is somewhere in PATH so this tool can be used
rem standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

rem Defer control.
python "%~dp0gsutil.py" %*
