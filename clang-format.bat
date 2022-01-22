@echo off
rem Copyright 2014 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.
setlocal

rem Ensure that "depot_tools" is somewhere in PATH so this tool can be used
rem standalone, but allow other PATH manipulations to take priority.
set PATH=%PATH%;%~dp0

rem Defer control.
python3 "%~dp0\clang_format.py" %*
