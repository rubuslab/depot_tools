@echo off
:: Copyright 2017 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

set DEPOT_TOOLS_DIR=%~1
call "%~dp0\cipd_bin_setup.bat" > "%DEPOT_TOOLS_DIR%.cipd.log" 2>&1
"%~dp0\.cipd_bin\led.exe" %*
