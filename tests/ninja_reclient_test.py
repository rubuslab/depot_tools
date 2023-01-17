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

import ninja_reclient


class NinjaReclientTest(unittest.TestCase):
  @unittest.mock.patch('subprocess.call', return_value=0)
  @unittest.mock.patch('ninja.main', return_value=0)
  @unittest.mock.patch('reclient_paths.find_reclient_bin_dir')
  @unittest.mock.patch('reclient_paths.find_reclient_cfg')
  def test_ninja_reclient(self, mock_reclient_cfg, mock_reclient_bin_dir,
                          mock_ninja, mock_call):
    argv = ["ninja_reclient.py", "-C", "out/a", "chrome"]
    reclient_bin_dir = "/path/to/reclient/bins"
    reclient_cfg = "/path/to/reclient/cfg/reproxy.cfg"
    mock_reclient_cfg.return_value = reclient_cfg
    mock_reclient_bin_dir.return_value = reclient_bin_dir

    ninja_reclient.main(argv)

    mock_ninja.assert_called_once_with(argv)
    mock_call.assert_has_calls([
        unittest.mock.call([
            os.path.join(reclient_bin_dir, "bootstrap"),
            "--re_proxy=" + os.path.join(reclient_bin_dir, "reproxy"),
            "--cfg=" + reclient_cfg
        ]),
        unittest.mock.call([
            os.path.join(reclient_bin_dir, "bootstrap"), "--shutdown",
            "--cfg=" + reclient_cfg
        ]),
    ])

  @unittest.mock.patch('subprocess.call', return_value=0)
  @unittest.mock.patch('ninja.main', side_effect=KeyboardInterrupt())
  @unittest.mock.patch('reclient_paths.find_reclient_bin_dir')
  @unittest.mock.patch('reclient_paths.find_reclient_cfg')
  def test_ninja_reclient_ninja_killed(self, mock_reclient_cfg,
                                       mock_reclient_bin_dir, mock_ninja,
                                       mock_call):
    argv = ["ninja_reclient.py", "-C", "out/a", "chrome"]
    reclient_bin_dir = "/path/to/reclient/bins"
    reclient_cfg = "/path/to/reclient/cfg/reproxy.cfg"
    mock_reclient_cfg.return_value = reclient_cfg
    mock_reclient_bin_dir.return_value = reclient_bin_dir

    ninja_reclient.main(argv)

    mock_ninja.assert_called_once_with(argv)
    mock_call.assert_has_calls([
        unittest.mock.call([
            os.path.join(reclient_bin_dir, "bootstrap"),
            "--re_proxy=" + os.path.join(reclient_bin_dir, "reproxy"),
            "--cfg=" + reclient_cfg
        ]),
        unittest.mock.call([
            os.path.join(reclient_bin_dir, "bootstrap"), "--shutdown",
            "--cfg=" + reclient_cfg
        ]),
    ])


if __name__ == '__main__':
  unittest.main()
