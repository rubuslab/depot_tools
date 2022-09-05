#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""This script will automatically try to find the ninja binary when run
inside the chrome source tree, so users can just type "ninja" on the command
line (normally depot_tools is on the path)."""

from __future__ import print_function

import gclient_paths
import os
import subprocess
import sys


def PruneVirtualEnv():
  # Set by VirtualEnv, no need to keep it.
  os.environ.pop('VIRTUAL_ENV', None)

  # Set by VPython, if scripts want it back they have to set it explicitly.
  os.environ.pop('PYTHONNOUSERSITE', None)

  # Look for "activate_this.py" in this path, which is installed by VirtualEnv.
  # This mechanism is used by vpython as well to sanitize VirtualEnvs from
  # $PATH.
  os.environ['PATH'] = os.pathsep.join([
      p for p in os.environ.get('PATH', '').split(os.pathsep)
      if not os.path.isfile(os.path.join(p, 'activate_this.py'))
  ])


def main(args):
  # Prune all evidence of VPython/VirtualEnv out of the environment. This means
  # that we 'unwrap' vpython VirtualEnv path/env manipulation. Invocations of
  # `python` from ninja should never inherit the ninja.py's own VirtualEnv. This
  # also helps to ensure that generated ninja files do not reference python.exe
  # from the VirtualEnv generated from depot_tools' own .vpython file (or lack
  # thereof), but instead reference the default python from the PATH.
  PruneVirtualEnv()

  # Try the ninja binary having been downloaded by CIPD in the project's DEPS.
  bin_path = gclient_paths.GetBuildtoolsPlatformBinaryPath()
  if not bin_path:
    print(
        'ninja.py: Could not find checkout in any parent of the current path.\n'
        'This must be run inside a checkout.',
        file=sys.stderr)
    return 1
  ninja_path = os.path.join(bin_path, 'ninja' + gclient_paths.GetExeSuffix())
  if not os.path.exists(ninja_path):
    print('ninja.py: Could not find ninja executable at: %s' % ninja_path,
          file=sys.stderr)
    return 2
  return subprocess.call([ninja_path] + args[1:])


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
