#!/usr/bin/env vpython3
# coding=utf-8
# Copyright (c) 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Tests for git_gerrit_cp.py"""

import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import git_gerrit_cp


class GitGerritCpTest(unittest.TestCase):

    def test_create_commit_message(self):
        orig_message = """Foo the bar

This change foo's the bar.

Bug: 123456
Change-Id: I25699146b24c7ad8776f17775f489b9d41499595
"""
        expected_message = """Cherry pick "Foo the bar"

Original change's description:
> Foo the bar
> 
> This change foo's the bar.
> 
> Bug: 123456
> Change-Id: I25699146b24c7ad8776f17775f489b9d41499595
"""
        self.assertEqual(git_gerrit_cp.create_commit_message(orig_message),
                         expected_message)

    def test_create_commit_message_with_bug(self):
        bug = "987654"
        orig_message = """Foo the bar

This change foo's the bar.

Bug: 123456
Change-Id: I25699146b24c7ad8776f17775f489b9d41499595
"""
        expected_message = f"""Cherry pick "Foo the bar"

Original change's description:
> Foo the bar
> 
> This change foo's the bar.
> 
> Bug: 123456
> Change-Id: I25699146b24c7ad8776f17775f489b9d41499595

Bug: {bug}
"""
        self.assertEqual(git_gerrit_cp.create_commit_message(orig_message, bug),
                         expected_message)


if __name__ == '__main__':
    unittest.main()
