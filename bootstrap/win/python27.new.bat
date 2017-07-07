@echo off
:: Copyright 2013 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

setlocal
set PATH=%~dp0python27_bin\bin;%~dp0python27_bin\bin\Scripts;%PATH%
"%~dp0python27_bin\bin\python.exe" %*
