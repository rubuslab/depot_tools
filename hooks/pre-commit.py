#!/usr/bin/env python3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""A git pre-commit hook to drop staged gitlink changes."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import git_common

staged = []
diff = git_common.run('diff-index', '--cached', 'HEAD')
for line in diff.splitlines():
    if not line.startswith(':160000 160000'):
        # Not a gitlink change.
        continue
    # Add the staged gitlink path.
    staged.append(line.split()[-1])

if not staged:
    exit(0)

option = 'depot-tools.allow-gitlink'
allowed = git_common.run('config', '--get', '--type=bool', option)
if allowed == 'true':
    print(f'{option} is true, committing.')
    exit(0)

deps_diff = git_common.run_with_retcode('diff', '--exit-code', '--cached',
                                        'HEAD', 'DEPS')
if deps_diff:
    print('Found gitlink and DEPS changes, committing.')
    exit(0)

print(
    f'Found no change to DEPS, unstaging {len(staged)} staged gitlink(s) found in diff:'
)
print(git_common.run(
    'diff',
    '--cached',
    'HEAD',
))
for path in staged:
    git_common.run('restore', '--staged', '--', path)

disable_msg = f'To disable this hook, run "git config {option} true"'
has_diff = git_common.run_with_retcode('diff', '--exit-code', '--cached',
                                       'HEAD')
if not has_diff:
    print('Found no changes, aborting commit.')
    print(disable_msg)
    exit(1)
print(disable_msg)
