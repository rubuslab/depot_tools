#!/usr/bin/env python
# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tool that allows you to quickly edit the working tree via diff.
"""

from __future__ import print_function

import argparse
import logging
import os
import subprocess2
import sys
import tempfile

import git_common
import setup_color


PREFIX = 'git-edit-diff-'


logging.getLogger().setLevel(logging.INFO)


def get_diff(revision):
  return git_common.diff(revision, 'HEAD')


def edit_file(filename):
  editor = os.environ.get('EDITOR', 'vi')
  subprocess2.check_call([editor, filename])


def reapply_diff(upstream, original_rev, diff_filename):
  """Reverts the branch back to upstream then applies the diff.

  Does not change the head, just the working tree.

  Args:
    upstream: revision that is the base of the diff.
    original_rev: revision that is currently checked out.
    diff_filename: file containing text diff.

  Returns:
    True on success, False if the patch failed to apply.
  """
  # Reset hard to the upstream. This keeps us on the same branch, but
  # temporarily destroys all the branch history.
  # TODO(mgiuca): Might be safer to use git checkout with all the files.
  git_common.run('reset', '--hard', upstream)
  # Reset mixed back to the original revision. This puts the branch history back
  # exactly where it was, but keeps the working tree equal to upstream.
  git_common.run('reset', original_rev)
  # Apply the updated diff.
  try:
    git_common.run('apply', diff_filename)
  except subprocess2.CalledProcessError as e:
    logging.error('%s', e.stderr)
    return False

  return True


def get_retry_choice():
  choice = ''
  while choice not in frozenset('eq'):
    choice = raw_input('(e)dit again / (q)uit? ').strip()

  return choice == 'q'


def do_edit_diff(upstream, original_rev):
  # Get the current diff against the upstream.
  diff = get_diff(upstream)
  # Allow the user to edit the diff directly.
  with tempfile.NamedTemporaryFile(mode='w+', prefix=PREFIX) as diff_file:
    diff_file.write(diff)
    # For some reason the diff doesn't end with a newline.
    diff_file.write('\n')
    diff_file.flush()
    diff_file.seek(0)
    done = False
    while not done:
      edit_file(diff_file.name)
      # Modify the working tree to match the upstream revision + new_diff.
      done = reapply_diff(upstream, original_rev, diff_file.name)

      if not done and get_retry_choice():
        return False

  return True


def main(args, stdout=sys.stdout, stderr=sys.stderr):
  parser = argparse.ArgumentParser(
      prog='git edit-diff',
      description='quickly edit the working tree via diff.')
  parser.add_argument('upstream', nargs='?', default='@{u}', metavar='UPSTREAM',
                      help='revision to diff against (default: @{u})')
  # TODO(mgiuca): Sub-args to forward to git diff.
  args = parser.parse_args(args)

  # Ensure no staged or unstaged changes.
  dirty = False
  for entry in git_common.status():
    if entry[1].lstat != '?' or entry[1].rstat != '?':
      dirty = True
  if dirty:
    logging.error('Working tree is dirty; cannot proceed.')
    return 1

  original_rev = git_common.run('rev-parse', 'HEAD')
  original_branch_or_rev = git_common.current_branch()
  if original_branch_or_rev == 'HEAD':
    original_branch_or_rev = original_rev
  completed = False
  try:
    completed = do_edit_diff(args.upstream, original_rev)
  finally:
    # If anything goes wrong, reset back to the original branch or revision.
    if not completed:
      git_common.run('reset', '--hard', original_branch_or_rev)

if __name__ == '__main__':  # pragma: no cover
  setup_color.init()
  with git_common.less() as less_input:
    sys.exit(main(sys.argv[1:], stdout=less_input))
