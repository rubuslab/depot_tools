#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Usage:
#    gclient-new-workdir.py [options] <repository> <new_workdir>
#

import argparse
import os
import shutil
import subprocess
import sys

import git_common


def parse_options():
  def print_err(msg):
    print(msg + '\n')
    parser.print_help()
    sys.exit(1)

  if sys.platform == 'win32':
    print('ERROR: This script cannot run on Windows because it uses symlinks.')
    sys.exit(1)

  parser = argparse.ArgumentParser(description='''\
      Clone an existing gclient directory, taking care of all sub-repositories.
      Works similarly to 'git new-workdir'.''')
  parser.add_argument('repository', help='should contain a .gclient file')
  parser.add_argument('new_workdir', help='must not exist')
  parser.add_argument('--reflink', action='store_true',
                      help='''use "cp --reflink" for speed and disk space.
                              need supported FS like btrfs or ZFS.''')
  args = parser.parse_args()

  args.repository = os.path.abspath(args.repository)

  if not os.path.exists(args.repository):
    print_err('ERROR: Repository "%s" does not exist.' % args.repository)

  gclient = os.path.join(args.repository, '.gclient')
  if not os.path.exists(gclient):
    print_err('ERROR: No .gclient file at "%s".' % gclient)

  if os.path.exists(args.new_workdir):
    print_err('ERROR: New workdir "%s" already exists.' % args.new_workdir)

  return args


def main():
  args = parse_options()

  gclient = os.path.join(args.repository, '.gclient')

  os.makedirs(args.new_workdir)
  os.symlink(gclient, os.path.join(args.new_workdir, '.gclient'))

  for root, dirs, _ in os.walk(args.repository):
    if '.git' in dirs:
      workdir = root.replace(args.repository, args.new_workdir, 1)
      print('Creating: %s' % workdir)

      if args.reflink:
        if not os.path.exists(workdir):
          print('Copying: %s' % workdir)
          subprocess.check_call(['cp', '-a', '--reflink', root, workdir])
        shutil.rmtree(os.path.join(workdir, '.git'))

      git_common.make_workdir(os.path.join(root, '.git'),
                              os.path.join(workdir, '.git'))
      if args.reflink:
        subprocess.check_call(['cp', '-a', '--reflink',
                              os.path.join(root, '.git', 'index'),
                              os.path.join(workdir, '.git', 'index')])
      else:
        subprocess.check_call(['git', 'checkout', '-f'], cwd=workdir)

      if args.reflink:
        subprocess.check_call(['git', 'clean', '-df'], cwd=workdir)


if __name__ == '__main__':
  sys.exit(main())
