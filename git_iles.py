#!/usr/bin/env python
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import fix_encoding
import git_common
import setup_color
import os
import subprocess2
import sys


def main(args):
  parser = argparse.ArgumentParser(
      formatter_class=argparse.ArgumentDefaultsHelpFormatter
  )
  parser.add_argument(
      'files', nargs='+',
      help='files to get urls for')
  # parser.add_argument(
  #     '-g', '--github',
  #     help='render Github url for mirrors from it')
  parser.add_argument(
      '-r', '--ref',
      help='which ref to resolve to a revision. Defaults to current branch '
           'remote upstream ref')
  parser.add_argument(
      '-c', '--chars', type=int, default=8,
      help='How many characters to abbreviate revision to')
  parser.add_argument(
      '-x', '--xclip', action='store_true',
      help='copies to X buffer by piping into xclip')

  opts = parser.parse_args(args)
  if not opts.files:
    parser.error('at least one file must be given')

  try:
    root = os.path.abspath(git_common.repo_root())
  except subprocess2.CalledProcessError:
    git_common.die('run this command inside git repo')

  remote = git_common.run('remote').strip().splitlines()[0]
  url = git_common.run('remote', 'get-url', remote).strip().rstrip('/')

  if not opts.ref:
    branch = git_common.current_branch()
    if branch == 'HEAD':
      opts.ref = branch
    else:
      branch_info = git_common.get_branches_info(True)
      while branch and branch_info.get(branch) is not None:
        branch = branch_info[branch].upstream
      if branch is None:
        opts.ref = '%s/master' % remote
      else:
        opts.ref = branch

  rev = git_common.hash_one(opts.ref)
  assert len(rev) == 40
  rev = rev[:opts.chars]

  def pl(f):
    if '#' in f:
      f, l = f.split('#')
    elif ':' in f:
      f, l = f.split(':')
    else:
      l = None
    p = os.path.relpath(os.path.abspath(f), root)
    if l is None:
      return p
    return p + '#' + l

  out = '\n'.join('%s/+/%s/%s' % (url, rev, pl(f)) for f in opts.files)
  print out

  if not opts.xclip:
    return 0
  xclip = subprocess2.Popen(['xclip', '-i', '-selection', 'clipboard'],
                            stdin=subprocess2.PIPE)
  return xclip.communicate(input=out)[0]


if __name__ == '__main__':
  # These affect sys.stdout so do it outside of main() to simplify mocks in
  # unit testing.
  fix_encoding.fix_encoding()
  setup_color.init()
  try:
    sys.exit(main(sys.argv[1:]))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
