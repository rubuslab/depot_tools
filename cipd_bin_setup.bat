@echo off
:: Copyright 2017 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

:: Installing the gcloud SDK from CIPD can take up to a minute due to its size.
:: We call "cipd ensure" below without any visible progress indicator, so users
:: might assume that the command is hanging or has crashed. Give them a hint
:: that this operation might take a while, so they know what's up.
cipd puppet-check-updates -ensure-file cipd_manifest.txt -root .cipd_bin 2>&1 | findstr /C:"infra/3pp/tools/gcloud/windows-" >nul
if %errorlevel% == 0 (
    echo Updating gcloud SDK, this might take a while...
)

"%~dp0\cipd.bat" ensure -log-level warning -ensure-file "%~dp0\cipd_manifest.txt" -root "%~dp0\.cipd_bin"
