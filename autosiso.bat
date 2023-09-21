@echo off
:: Copyright 2023 The Chromium Authors
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal

set scriptdir=%~dp0

echo "FYI: autosiso has been merged into autoninja, which will now"
echo "     automatically delegate to the right tool depending on your"
echo "     GN args. Please run autoninja going forward."

:: Ensure that "depot_tools" is somewhere in PATH so this tool can be used
:: standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

if "%*" == "/?" (
  rem Handle "autosiso /?" which will otherwise give help on the "call" command
  @call %scriptdir%python-bin\python3.bat %scriptdir%autoninja.py --help
  exit /b
)

:: Defer control to autoninja.
:: Add double quotes to the arguments to preserve the special '^' character.
:: See autosiso.py for more information.
@call "%scriptdir%autoninja.bat" "%*"
