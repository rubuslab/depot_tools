#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""This script is a wrapper around the ninja binary that is pulled to
third_party as part of gclient sync. It will automatically find the ninja
binary when run inside a gclient source tree, so users can just type
"ninja" or "ninja.exe" on the command line."""

import gclient_paths
import os
import subprocess
import sys


DEPOT_TOOLS_ROOT = os.path.abspath(os.path.dirname(__file__))


def main(args):
  # Get gclient root + src.
  primary_solution_path = gclient_paths.GetPrimarySolutionPath()
  if not primary_solution_path:
    print(
      'depot_tools/ninja.py: Could not find checkout in any parent of the '
      'current path.\nThis must be run inside a checkout.', file=sys.stderr)
    return 1
  ninja_path = os.path.join(primary_solution_path, 'third_party',
                         'ninja', 'ninja' + gclient_paths.GetExeSuffix())
  if not os.path.exists(ninja_path):
    print('depot_tools/ninja.py: Could not find ninja executable at: %s'
          % ninja_path, file=sys.stderr)
    return 1

  return subprocess.call([ninja_path] + args[1:])


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
