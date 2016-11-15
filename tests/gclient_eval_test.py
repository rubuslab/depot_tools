#!/usr/bin/env python
# Copyright (c) 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit tests for gclient_eval.py."""

# pylint: disable=E1103

import logging
import sys
import unittest

import gclient_eval

class EvalTest(unittest.TestCase):
  def check(self, contents, exp):
    try:
      gclient_eval.Check(contents, '', exp)
    except gclient_eval.CheckFailure as ex:
      self.assertEqual(ex.exp, ex.got)

  def test_eval_sample_dot_gclient(self):
    self.check('''\
        solutions = [{
          "name" : "src",
          "url"  : "https://chromium.googlesource.com/chromium/src.git",
          }]
        ''', {
          'solutions': [{
            'name': 'src',
            'url': 'https://chromium.googlesource.com/chromium/src.git',
          }],
        })

  def test_eval_backslashes(self):
    self.check('hooks = [{"pattern": "\\\\.sha1"}]\n',
               {'hooks': [{'pattern': '\\.sha1'}]})

  def test_nested_dicts(self):
    self.check('deps_os = {"win": {}, "mac": {}}\n',
               {'deps_os': {'win': {}, 'mac': {}}})



if __name__ == '__main__':
  level = logging.DEBUG if '-v' in sys.argv else logging.FATAL
  logging.basicConfig(
      level=level,
      format='%(asctime).19s %(levelname)s %(filename)s:'
             '%(lineno)s %(message)s')
  unittest.main()

# vim: ts=2:sw=2:tw=80:et:
