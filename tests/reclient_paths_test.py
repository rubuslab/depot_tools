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


@unittest.mock.patch.dict('os.environ', {
    reclient_paths.BIN_DIR_ENV_KEY: None,
    reclient_paths.CFG_ENV_KEY: None,
})
class ReclientPathsTest(gclient_paths_test.TestBase):
  def test_find_reclient_bin_dir_from_env(self):
    self.make_file_tree({
        os.path.join("path", "to", "reclient", "version.txt"):
        "content",
    })
    os.environ[reclient_paths.BIN_DIR_ENV_KEY] = (os.path.join(
        self.root, "path", "to", "reclient"))

    self.assertEqual(os.path.join(self.root, "path", "to", "reclient"),
                     reclient_paths.find_reclient_bin_dir())

  def test_find_reclient_bin_dir_from_gclient(self):
    self.make_file_tree({
        '.gclient':
        '',
        '.gclient_entries':
        'entries = {"buildtools": "..."}',
        os.path.join("src", "buildtools", "reclient", "version.txt"):
        "content",
    })

    self.assertEqual(os.path.join(self.root, "src", "buildtools", "reclient"),
                     reclient_paths.find_reclient_bin_dir())
    self.assertEqual(os.path.join(self.root, "src", "buildtools", "reclient"),
                     os.environ[reclient_paths.BIN_DIR_ENV_KEY])

  def test_find_reclient_bin_dir_from_gclient_not_found(self):
    self.make_file_tree({
        '.gclient': '',
    })
    with self.assertRaises(reclient_paths.NotFoundError):
      reclient_paths.find_reclient_bin_dir()
    self.assertEqual(None, os.environ[reclient_paths.BIN_DIR_ENV_KEY])

  def test_find_reclient_cfg_from_env(self):
    self.make_file_tree({
        os.path.join("path", "to", "reproxy.cfg"): "content",
    })
    os.environ[reclient_paths.CFG_ENV_KEY] = (os.path.join(
        self.root, "path", "to", "reproxy.cfg"))

    self.assertEqual("/path/to/reproxy.cfg", reclient_paths.find_reclient_cfg())

  def test_find_reclient_cfg_from_gclient(self):
    self.make_file_tree({
        '.gclient':
        '',
        '.gclient_entries':
        'entries = {"buildtools": "..."}',
        os.path.join("src", "buildtools", "reclient_cfgs", "reproxy.cfg"):
        "content",
    })

    self.assertEqual(
        os.path.join(self.root, "src", "buildtools", "reclient_cfgs",
                     "reproxy.cfg"), reclient_paths.find_reclient_cfg())
    self.assertEqual(
        os.path.join(self.root, "src", "buildtools", "reclient_cfgs",
                     "reproxy.cfg"), os.environ[reclient_paths.CFG_ENV_KEY])

  def test_find_reclient_cfg_from_gclient_not_found(self):
    self.make_file_tree({
        '.gclient': '',
    })
    with self.assertRaises(reclient_paths.NotFoundError):
      reclient_paths.find_reclient_cfg()
    self.assertEqual(None, os.environ[reclient_paths.CFG_ENV_KEY])


if __name__ == '__main__':
  unittest.main()
