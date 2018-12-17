#!/usr/bin/env python
# Copyright (c) 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import ninjalog_uploader


class NinjalogUploaderTest(unittest.TestCase):
    def test_parse_gn_args(self):
        self.assertEqual(ninjalog_uploader.ParseGNArgs('[]'), {})
        self.assertEqual(ninjalog_uploader.ParseGNArgs('[{\
        "current": {"value": "true"}, \
        "default": {"value": "false"}, \
        "name": "is_component_build"}]'), {u'is_component_build': u'true'})

    def test_get_ninjalog(self):
        self.assertEqual(ninjalog_uploader.GetNinjalog(['ninja']), './.ninja_log')
        self.assertEqual(ninjalog_uploader.GetNinjalog(['ninja', '-C', 'out/Release']),
                         'out/Release/.ninja_log')
        self.assertEqual(ninjalog_uploader.GetNinjalog(['ninja', '-Cout/Release']),
                         'out/Release/.ninja_log')
        self.assertEqual(ninjalog_uploader.GetNinjalog(['ninja', '-C']),
                         './.ninja_log')
        self.assertEqual(ninjalog_uploader.GetNinjalog(
            ['ninja', '-C', 'out/Release', '-C', 'out/Debug']),
            'out/Debug/.ninja_log')


if __name__ == '__main__':
    unittest.main()
