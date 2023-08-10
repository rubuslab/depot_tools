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

import subprocess
from typing import List

# The status prefix is something like '?? ' or 'M  '
STATUS_PREFIX_LENGTH = 3


def get_files() -> List[str]:
  """Return a list of non-submodule changes from the cwd."""
  # --ignore-submodules=all  -- always ignores submodules in a status.
  # --procelain              -- produce stable, script-friendly output
  #  -z                      -- use \x00 to separate lines not \n.
  output = subprocess.check_output(
      ["git", "status", "--ignore-submodules=all", "--porcelain", "-z"],
      encoding='utf-8',
  )
  lines = output.split("\x00")
  out = []
  for line in lines:
    line = line[STATUS_PREFIX_LENGTH:].rstrip("\x00")
    # annoyingly, the last line is an empty string.
    if line:
      out.append(line)
  return out


def main():
  """Add non-submodule changes from the cwd."""
  subprocess.check_call(["git", "add", "--"] + get_files())


if __name__ == "__main__":
  main()
