#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Developers invoke this script via autosiso or autosiso.bat to simply run
Siso builds.
"""

import os
import subprocess
import sys

import reclient_helper

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))


def main(argv):
  with reclient_helper.build_context(argv) as ret_code:
    if ret_code:
      return ret_code
    siso_path = os.path.join(SCRIPT_DIR, 'siso.py')
    return subprocess.call([sys.executable, siso_path, 'ninja'] + argv[1:])


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.exit(1)
