# Copyright (c) 2021 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

if sys.version_info.major == 2:
  import mock
else:
  from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import split_cl


class DepotToolsClientTest(unittest.TestCase):
  @mock.patch('os.path.isfile')
  def testGetFilesSplitByOwners(self, mockIsfile):
    mockIsfile.side_effect = lambda f: f in ['a/b/OWNERS', 'a/OWNERS']
    modified_files = [
      ('M', 'a/b/c'),
      ('M', 'a/b/d'),
      ('M', 'a/e/f/g'),
    ]
    self.assertEqual(
        {'a/b': [('M', 'a/b/c'), ('M', 'a/b/d')], 'a': [('M', 'a/e/f/g')]},
        split_cl.GetFilesSplitByOwners(modified_files))


if __name__ == '__main__':
  unittest.main()
