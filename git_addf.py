#!/usr/bin/env python3

# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Intended use case:
#
# $ git status --ignore-submodules=none
# some output, including files and submodules
#
# $ git addf
#
# git commit -m 'some commit message'
#
# $ git status --ignore-submodules=none
# some output, but only in submodules.

# TODO:
#  1) Have an informative error message rather than a stack trace
#     when not in a git repo.
#  2) Support -p flag for interactively adding chunks at a time.
#  3) Support specifying files to add.

import sys
import subprocess
from typing import List

import git_common


def get_files() -> List[str]:
  """Return a list of non-submodule changes from the cwd."""
  out = []
  for (f, _) in git_common.status(ignore_submodules='all'):
    out.append(f)
  return out


def main(argv: List[str]) -> int:
  """Add non-submodule changes from the cwd."""
  if argv:
    raise ValueError("git addf does not support any arguments yet")
  return git_common.run_with_retcode("add", "--", *get_files())


if __name__ == "__main__":
  sys.exit(main(sys.argv[1:]))
