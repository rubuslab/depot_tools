echo off
rem Copyright (c) 2018 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.
setlocal

rem Defer control.
python3 "%~dp0fake_cipd.py" %*
