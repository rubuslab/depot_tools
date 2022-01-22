@echo off
rem Copyright (c) 2012 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.
setlocal

rem Shall skip automatic update?
IF "%DEPOT_TOOLS_UPDATE%" == "0" GOTO :CALL_GCLIENT

rem Synchronize the root directory before deferring control back to gclient.py.
call "%~dp0update_depot_tools.bat" %*
rem Abort the script if we failed to update depot_tools.
IF %errorlevel% NEQ 0 (
  goto :EOF
)

:CALL_GCLIENT
rem Ensure that "depot_tools" is somewhere in PATH so this tool can be used
rem standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

rem Defer control.
IF "%GCLIENT_PY3%" == "1" (
  rem Explicitly run on Python 3
  call vpython3 "%~dp0gclient.py" %*
) ELSE IF "%GCLIENT_PY3%" == "0" (
  rem Explicitly run on Python 2
  call vpython "%~dp0gclient.py" %*
) ELSE (
  rem Run on Python 3, allows default to be flipped.
  call vpython3 "%~dp0gclient.py" %*
)
