#!/usr/bin/env vpython3
# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for rdb_wrapper.py"""

from __future__ import print_function

import os
import logging
import sys
import unittest
#add imports Here

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rdb_wrapper
import subprocess2

class TestSetupRDB(unittest.TestCase):
  def setUp(self):
      #super(TestSetupRDB, self).setUp()
      #mock.patch(??? ARE THERE THINGS WE ARE TRYING TO MOCK HERE?)
      pass

  def test_setup_rdb(self):
      # expected_results = False
      #self.assertEQUAL?! YOU NEED TO USE SOME ASSERT STATEMENT HERE!
      pass

if __name__ == '__main__':
  logging.basicConfig(
      level=logging.DEBUG if '-v' in sys.argv else logging.ERROR)
  unittest.main()
