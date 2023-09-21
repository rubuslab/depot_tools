@echo off
:: Copyright 2023 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal

set scriptdir=%~dp0

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

if "%*" == "/?" (
  rem Handle "siso /?" which will otherwise give help on the "call" command
  @call %scriptdir%python-bin\python3.bat %scriptdir%siso.py --help
  exit /b
)

:: Defer control.
@call %scriptdir%python-bin\python3.bat %scriptdir%siso.py "%*"
