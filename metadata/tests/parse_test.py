#!/usr/bin/env vpython3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.dirname(os.path.dirname(CURRENT_DIRECTORY)))

from metadata.parse import parse_file
from metadata.model import Metadata, Metadatum


def get_test_filepath(filename: str):
  return os.path.join(CURRENT_DIRECTORY, "data", filename)


class ParseTest(unittest.TestCase):
  def test_parse(self):
    filepath = get_test_filepath("README.chromium.test.multi")
    all_metadata = parse_file(filepath)

    self.assertEqual(all_metadata, [
        Metadata([
            Metadatum(
                "Name",
                "Test-A README for Chromium metadata parsing and validation"),
            Metadatum("Short Name", "metadata-test-valid"),
            Metadatum(
                "URL", "https://www.example.com/metadata,\n"
                "     https://www.example.com/parser"),
            Metadatum("Version", "1.0.12"),
            Metadatum("Date", "2020-12-03"),
            Metadatum("License", "Apache, 2.0"),
            Metadatum("License File", "LICENSE"),
            Metadatum("Security Critical", "yes"),
            Metadatum("Shipped", "yes"),
            Metadatum("CPEPrefix", "unknown"),
            Metadatum(
                "Description", "A test metadata file, with a\n"
                " multi-line description."),
            Metadatum("Local Modifications", "None"),
        ]),
        Metadata([
            Metadatum(
                "Name",
                "Test-B README for Chromium metadata parsing and validation"),
            Metadatum(" Short Name", "metadata-test-invalid"),
            Metadatum("URL", "file://home/drive/chromium/src/metadata"),
            Metadatum("Version", "0"),
            Metadatum("Date", "2020-12-03"),
            Metadatum("License", "MIT"),
            Metadatum("Security critical", "yes"),
            Metadatum("Shipped", "Yes"),
            Metadatum("Description", ""),
            Metadatum("Local Modifications", "None,\n"
                      "EXCEPT:\n"
                      "* nothing.    "),
        ]),
        Metadata([
            Metadatum(
                "Name",
                "Test-C README for Chromium metadata parsing and validation"),
            Metadatum("URL", "https://www.example.com/first"),
            Metadatum("URL", "https://www.example.com/second"),
            Metadatum("Version", "N/A"),
            Metadatum("Date", "2020-12-03"),
            Metadatum("License", "Custom license"),
            Metadatum("Security Critical", "yes"),
            Metadatum(
                "Description", "Test metadata with multiple entries for one "
                "field, and\nmissing a mandatory field."),
        ])
    ])


if __name__ == "__main__":
  unittest.main()
