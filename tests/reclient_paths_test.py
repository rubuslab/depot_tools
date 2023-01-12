#!/usr/bin/env vpython3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import os.path
import sys
import unittest
import unittest.mock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import reclient_paths
import gclient_paths_test
from testing_support import trial_dir


def write(filename, content):
  """Writes the content of a file and create the directories as needed."""
  filename = os.path.abspath(filename)
  dirname = os.path.dirname(filename)
  if not os.path.isdir(dirname):
    os.makedirs(dirname)
  with open(filename, 'w') as f:
    f.write(content)


class ReclientPathsTest(trial_dir.TestCase):
  def setUp(self):
    super(ReclientPathsTest, self).setUp()
    self.previous_dir = os.getcwd()
    os.chdir(self.root_dir)
    unittest.mock.patch('os.environ', {}).start()
    self.addCleanup(unittest.mock.patch.stopall)

  def tearDown(self):
    os.chdir(self.previous_dir)
    super(ReclientPathsTest, self).tearDown()

  def test_find_reclient_bin_dir_from_env(self):
    write(os.path.join("path", "to", "reclient", "version.txt"), '0.0')
    os.environ[reclient_paths.BIN_DIR_ENV_KEY] = (os.path.join(
        self.root_dir, "path", "to", "reclient"))

    self.assertEqual(os.path.join(self.root_dir, "path", "to", "reclient"),
                     reclient_paths.find_reclient_bin_dir())

  def test_find_reclient_bin_dir_from_gclient(self):
    write('.gclient', '')
    write('.gclient_entries', 'entries = {"buildtools": "..."}')
    write(os.path.join('src', 'buildtools', 'reclient', 'version.txt'), '0.0')

    self.assertEqual(
        os.path.join(self.root_dir, 'src', 'buildtools', 'reclient'),
        reclient_paths.find_reclient_bin_dir())
    self.assertEqual(
        os.path.join(self.root_dir, 'src', 'buildtools', 'reclient'),
        os.environ[reclient_paths.BIN_DIR_ENV_KEY])

  def test_find_reclient_bin_dir_from_gclient_not_found(self):
    with self.assertRaises(reclient_paths.NotFoundError):
      reclient_paths.find_reclient_bin_dir()

    self.assertNotIn(reclient_paths.BIN_DIR_ENV_KEY, os.environ)

  def test_find_reclient_cfg_from_env(self):
    write(os.path.join('path', 'to', 'reproxy.cfg'), 'RBE_v=2')
    os.environ[reclient_paths.CFG_ENV_KEY] = (os.path.join(
        self.root_dir, 'path', 'to', 'reproxy.cfg'))

    self.assertEqual(os.path.join(self.root_dir, 'path', 'to', 'reproxy.cfg'),
                     reclient_paths.find_reclient_cfg())

  def test_find_reclient_cfg_from_gclient(self):
    write('.gclient', '')
    write('.gclient_entries', 'entries = {"buildtools": "..."}')
    write(os.path.join('src', 'buildtools', 'reclient_cfgs', 'reproxy.cfg'),
          '0.0')

    self.assertEqual(
        os.path.join(self.root_dir, 'src', 'buildtools', 'reclient_cfgs',
                     'reproxy.cfg'), reclient_paths.find_reclient_cfg())
    self.assertEqual(
        os.path.join(self.root_dir, 'src', 'buildtools', 'reclient_cfgs',
                     'reproxy.cfg'), os.environ[reclient_paths.CFG_ENV_KEY])

  def test_find_reclient_cfg_from_gclient_not_found(self):
    with self.assertRaises(reclient_paths.NotFoundError):
      reclient_paths.find_reclient_cfg()

    self.assertNotIn(reclient_paths.CFG_ENV_KEY, os.environ)


if __name__ == '__main__':
  unittest.main()
