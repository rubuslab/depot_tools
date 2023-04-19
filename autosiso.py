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

# Reclient flags for Siso builds.
RECLIENT_FLAGS = {
    'RBE_use_unified_uploads': 'false',
}


def set_reclient_flags():
  """Set Reclient flags for Siso builds."""
  for k, v in RECLIENT_FLAGS.items():
    os.environ.setdefault(k, v)


def main(argv):
  set_reclient_flags()
  with reclient_helper.build_context(argv) as ret_code:
    if ret_code:
      return ret_code
    siso_cmd = [
        sys.executable,
        os.path.join(SCRIPT_DIR, 'siso.py'),
        'ninja',
        # Do not authenticate when using Reproxy.
        '-project=',
        '-reapi_instance=',
    ] + argv[1:]
    return subprocess.call(siso_cmd)


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.exit(1)
