@echo off
rem Copyright 2019 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.

rem See revert instructions in cipd_manifest.txt

set scriptdir=%~dp0

@call "%~dp0\cipd_bin_setup.bat" > nul 2>&1
@call %scriptdir%python-bin\python3.bat %~dp0\.cipd_bin\goma_auth.py %*
exit /b
