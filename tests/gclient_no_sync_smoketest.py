#!/usr/bin/env vpython3
# Copyright (c) 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Smoke tests for gclient.py and the no-sync experiment

Shell out 'gclient' and run git tests.
"""

import json
import logging
import os
import sys
import unittest

import gclient_smoketest_base

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import subprocess2
from testing_support.fake_repos import join, write


class GClientSmokeGIT(gclient_smoketest_base.GClientSmokeBase):
  """Smoke tests for the no-sync experiment."""

  FAKE_REPOS_CLASS = fake_repos.FakeRepoNoSyncDEPS


  def setUp(self):
    super(GClientSmokeGIT, self).setUp()
    self.env['PATH'] = (os.path.join(ROOT_DIR, 'testing_support')
                        + os.pathsep + self.env['PATH'])
    self.enabled = self.FAKE_REPOS.set_up_git()
    if not self.enabled:
      self.skipTest('git fake repos not available')

  def testNoSync(self):
    """ """
    self.gclient(['config', self.git_base + 'repo_1', '--name', 'src'])

    output_json = os.path.join(self.root_dir, 'output.json')

    self.parseGclient(
        ['sync', '--skip-sync-revisions', 'src@??????', '--output-json', output_json])

    with open(output_json) as f:
      output_json = json.load(f)

    out = {}
    self.assertEqual(out, output_json)
