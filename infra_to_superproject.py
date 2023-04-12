#!/usr/bin/env python3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Creates a new infra_superpoject gclient checkout based on an existing
infra or infra_internal checkout.

  Usage:

  (1) Commit any WIP changes in all infra repos:
      `git commit -a -v -m "another commit" OR `git commit -a -v --amend`

  (2) Run `git rebase-update` and `gclient sync` and ensure all conflicts
      are resolved.

  (3) In your gclient root directory (the one that contains a .gclient file),
      run:
      `python3 path/to/depot_tools/infra_to_superproject.py <destination>`
      example:
     `cd ~/cr`  # gclient root dir
     `python3 depot_tools/infra_to_superproject.py ~/cr2`

  (4) `cd <destination>` and check that everything looks like your original
      gclient checkout. The file structure should be the same, your branches
      and commits in repos should be copied over.

  (5) `sudo rm -rf <old_directory_name>`
      example:
      `sudo rm -rf cr`

  (6) `mv <destination> <old_directory_name>`
      example:
      `mv cr2 cr

"""

import subprocess
import os
import platform
import sys
import shutil
import json
from pathlib import Path


def main(argv):
  source = os.getcwd()
  backup = source + '_backup'

  print(f'Creating backup in {backup}')
  shutil.copytree(source, backup, symlinks=True, dirs_exist_ok=True)
  print('backup complete')

  print(f'Deleting old {source}/.gclient file')
  gclient_file = os.path.join(source, '.gclient')
  with open(gclient_file, 'r') as file:
    data = file.read()
    internal = "infra_internal" in data
  os.remove(gclient_file)

  print('Migrating to infra/infra_superproject')
  cmds = ['fetch', '--force']
  if internal:
    cmds.append('infra_internal')
    print('including internal code in checkout')
  else:
    cmds.append('infra')
  fetch = subprocess.Popen(cmds, cwd=source)
  fetch.wait()


if __name__ == '__main__':
  sys.exit(main(sys.argv[1:]))
