#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Run a pinned gsutil.

Calls into the 'depot_tools' recipe module's 'gsutil.py' resource.
"""

import os
import subprocess
import sys


DEPOT_TOOLS_ROOT = os.path.abspath(os.path.dirname(__file__))


if __name__ == '__main__':
  gsutil_py = os.path.join(DEPOT_TOOLS_ROOT, 'recipe_modules', 'gsutil',
                           'resources', 'gsutil.py')
  rc = subprocess.call(
      [sys.executable, gsutil_py] + sys.argv[1:])
  sys.exit(rc)
