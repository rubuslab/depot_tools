#!/usr/bin/env python
# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
import re
import shutil
import sys


CIPD_SUBDIR_RE = '@Subdir (.*)'

def main():
  assert sys.argv[1] == 'ensure'
  parser = argparse.ArgumentParser()
  parser.add_argument('-ensure-file')
  parser.add_argument('-root')
  args, _ = parser.parse_known_args()

  if args.ensure_file:
    shutil.copy(args.ensure_file, os.path.join(args.root, '_cipd'))

  with open(args.ensure_file) as f:
    ensure_content = f.readlines()

  current_file = None
  for line in ensure_content:
    match = re.match(CIPD_SUBDIR_RE, line)
    if match:
      subdir = os.path.join(args.root, *match.group(1).split('/'))
      if not os.path.isdir(subdir):
        os.makedirs(subdir)
      current_file = os.path.join(subdir, '_cipd')
    elif current_file:
      with open(current_file, 'a') as f:
        f.write(line)

  return 0


if __name__ == '__main__':
  sys.exit(main())
