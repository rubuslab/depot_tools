@echo off
:: Copyright 2017 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

for /f %%i in (%~dp0python_bin_reldir.txt) do set PYTHON_BIN_RELDIR=%%i
set PATH=%~dp0%PYTHON_BIN_RELDIR%;%~dp0%PYTHON_BIN_RELDIR%\Scripts;%PATH%

call "%~dp0\cipd_bin_setup.bat" > nul 2>&1
"%~dp0\.cipd_bin\vpython.exe" -vpython-interpreter "%PYTHON_BIN_RELDIR%\python.exe" %*
