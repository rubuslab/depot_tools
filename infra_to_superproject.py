#!/usr/bin/env python3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Creates a new infra_superpoject gclient checkout based on an existing infra
   of infra_superproject.

  usage: in your gclient root directory (the one that contains a .gclient file),
  run: `python infra_to_superproject.py`
"""

import subprocess
import argparse
import os
import sys
import json
from pathlib import Path


def main(argv):
  parser = argparse.ArgumentParser("Gclient migration.")
  parser.add_argument('--destination',
                      default='~/cr2',
                      help="Location of the new directory. Default '~/cr2'")
  options = parser.parse_args(argv)

  Path(options.destination).mkdir(parents=True, exist_ok=True)

  cp = subprocess.Popen(['cp', '-a', os.getcwd() + '/.', options.destination])
  cp.wait()

  gclient_file = os.path.join(options.destination, '.gclient')
  with open(gclient_file, 'r') as file:
    data = file.read()
    internal = "infra_internal" in data

  os.remove(gclient_file)

  cmds = ['fetch', '--force']
  if internal:
    cmds.append('infra_internal')
  else:
    cmds.append('infra')
  fetch = subprocess.Popen(cmds, cwd=options.destination)
  fetch.wait()


if __name__ == '__main__':

  sys.exit(main(sys.argv[1:]))
