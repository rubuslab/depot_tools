@echo off
:: Copyright 2024 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal

:: See revert instructions in cipd_manifest.txt

call "%~dp0\cipd_bin_setup.bat"

:: The "gcloud.cmd" script provided in the gcloud SDK assumes that Python is
:: an .exe file and fails when we point it to our usual python3.bat.
:: Thus, let's get the path to our actual python3.exe and use that as the
:: interpreter for gcloud SDK.
for /f %%i in (%~dp0python3_bin_reldir.txt) do set PYTHON3_BIN_RELDIR=%%i
set PATH=%~dp0%PYTHON3_BIN_RELDIR%;%~dp0%PYTHON3_BIN_RELDIR%\Scripts;%PATH%
set CLOUDSDK_PYTHON="%~dp0%PYTHON3_BIN_RELDIR%\python3.exe"

call "%~dp0\.cipd_bin\bin\gcloud.cmd" %*
