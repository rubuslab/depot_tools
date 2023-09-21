#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Developers invoke this script via autosiso or autosiso.bat to simply run
Siso/Reclient builds.
"""

import sys

import autoninja

if __name__ == '__main__':
    sys.exit(autoninja.main(sys.argv))
