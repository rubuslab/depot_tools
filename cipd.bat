@echo off
:: Copyright (c) 2016 The Chromium Authors. All rights reserved.
:: Use of this source code is governed by a BSD-style license that can be
:: found in the LICENSE file.

set /p BUILD=<"%~dp0\cipd_client_version"

"%~dp0\.cipd_client.exe" selfupdate -version %BUILD%
"%~dp0\.cipd_client.exe" %*
