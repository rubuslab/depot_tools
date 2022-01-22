@echo off
rem Copyright 2017 The Chromium Authors. All rights reserved.
rem Use of this source code is governed by a BSD-style license that can be
rem found in the LICENSE file.

"%~dp0\cipd.bat" ensure -log-level warning -ensure-file "%~dp0\cipd_manifest.txt" -root "%~dp0\.cipd_bin"
