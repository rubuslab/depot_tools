#!/usr/bin/env vpython3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest
from unittest import mock

DEPOT_TOOLS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, DEPOT_TOOLS_ROOT)

import git_addf

# These unit tests leave a bit to be desired. I would prefer to create a local
# repo in a temporary directory, initialize it, add a few files, and then call
# `git addf`, exercising all the `git` machinery, and confirming that the
# staging area has what I expect in it.


class GitAddfTest(unittest.TestCase):
  @mock.patch('git_common.status')
  def testAddfOnEmptyRepo(self, status_mock):
    """test running git_addf.files() on a repo with no changes in it."""
    status_mock.return_value = []
    self.assertEqual(git_addf.get_files(), [])

  @mock.patch('git_common.status')
  def testAddfOnNonEmptyRepo(self, status_mock):
    """test running git_addf.files() on a repo with a dirty repo."""
    status_mock.return_value = [("/path/to/a.txt", None)]
    self.assertEqual(git_addf.get_files(), ["/path/to/a.txt"])


if __name__ == "__main__":
  unittest.main()
