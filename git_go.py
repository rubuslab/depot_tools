#!/usr/bin/env python
# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Go to the upstream/downstream of the current branch."""

from __future__ import print_function

import argparse
import sys

import subprocess2

from git_common import run, get_branch_tree, current_branch

import git_rebase_update

def main(args):
  parser = argparse.ArgumentParser()
  parser.add_argument('where', choices=('up', 'down'))
  opts = parser.parse_args(args)

  branch = current_branch()

  if branch == 'HEAD' or not branch:
    parser.error('Must be on the branch you want to move from')

  skipped, tree = get_branch_tree()
  if branch in skipped:
    parser.error('Must have proper upstream')

  if 'down' == opts.where:
    children = [child for child, parent in tree.items() if parent == branch]
    if not children:
      parser.error('No downstream branch identified')
    elif len(children) > 1:
      parser.error('Possible downstreams:\n%s' % ('\n'.join(children),))
    else:
      run('checkout', children[0])
    return 0

  assert 'up' == opts.where, opts.where
  if branch not in tree:
    parser.error('No upsttream identified')
  else:
    run('checkout', tree[branch])
  return 0


if __name__ == '__main__':  # pragma: no cover
  try:
    sys.exit(main(sys.argv[1:]))
  except KeyboardInterrupt:
    sys.stderr.write('interrupted\n')
    sys.exit(1)
