@echo off
:: Copyright 2017 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.
setlocal
call "%~dp0\cipd_bin_setup.bat"
if not defined EDITOR set EDITOR=notepad
set PATH=%~dp0.cipd_bin\cmd;%PATH%
"%~dp0\.cipd_bin\usr\bin\ssh.exe" %*
