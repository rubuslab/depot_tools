@echo off
rem Copyright 2018 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.

rem See revert instructions in cipd_manifest.txt

call "%~dp0\cipd_bin_setup.bat" > nul 2>&1
"%~dp0\.cipd_bin\luci-auth.exe" %*

