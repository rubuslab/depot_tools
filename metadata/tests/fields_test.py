#!/usr/bin/env vpython3
# Copyright (c) 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
from typing import Callable, List, Union
import unittest

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))

import metadata.fields as fields
from metadata.util import ValidationError, ValidationResult, ValidationWarning


class FieldValidationTest(unittest.TestCase):
  def _run_field_validation(self,
                            validator: Callable[[str], Union[ValidationResult,
                                                             None]],
                            valid_values: List[str],
                            error_values: List[str],
                            warning_values: List[str] = []):
    for value in valid_values:
      self.assertIsNone(validator(value))

    for value in error_values:
      self.assertIsInstance(validator(value), ValidationError)

    for value in warning_values:
      self.assertIsInstance(validator(value), ValidationWarning)

  def _run_yes_no_field_validation(self,
                                   validator: Callable[[str],
                                                       Union[ValidationResult,
                                                             None]]):
    self._run_field_validation(validator=validator,
                               valid_values=["yes", "no"],
                               error_values=["", "\n", "yes\t", "    no"],
                               warning_values=["No", "YES"])

  def test_name_validation(self):
    self._run_field_validation(
        validator=fields.NameField.validate,
        valid_values=["Test dependency name"],
        error_values=["", "\n"],
    )

  def test_short_name_validation(self):
    self._run_field_validation(
        validator=fields.ShortNameField.validate,
        valid_values=["t-dep-name"],
        error_values=["", "\n"],
    )

  def test_url_validation(self):
    self._run_field_validation(
        validator=fields.URLField.validate,
        valid_values=[
            "https://www.example.com/a",
            "http://www.example.com/b",
            "ftp://www.example.com/c",
            "git://www.example.com/d",
            "This is the canonical public repository",
        ],
        error_values=[
            "", "\n", "ghttps://www.example.com/e",
            "https://www.example.com/ f", "Https://www.example.com/g",
            "This is an unrecognized message for the URL"
        ],
    )

  def test_version_validation(self):
    self._run_field_validation(
        validator=fields.VersionField.validate,
        valid_values=["N/A", "123abc", "unknown forked version"],
        error_values=["", "\n"],
        warning_values=["0"],
    )

  def test_date_validation(self):
    self._run_field_validation(
        validator=fields.DateField.validate,
        valid_values=["2012-03-04"],
        error_values=["", "\n", "April 3, 2012", "2012/03/04"],
    )

  def test_revision_validation(self):
    self._run_field_validation(
        validator=fields.RevisionField.validate,
        valid_values=["abc123", "revision description and not an ID"],
        error_values=["", "\n"],
    )

  def test_license_validation(self):
    pass

  def test_license_file_validation(self):
    pass

  def test_security_critical_validation(self):
    self._run_yes_no_field_validation(fields.SecurityCriticalField.validate)

  def test_shipped_validation(self):
    self._run_yes_no_field_validation(fields.ShippedField.validate)

  def test_license_android_compatible_validation(self):
    self._run_yes_no_field_validation(
        fields.LicenseAndroidCompatibleField.validate)

  def test_cpe_prefix_validation(self):
    self._run_field_validation(validator=fields.CPEPrefixField.validate,
                               valid_values=[
                                   "unknown", "cpe:/a:sqlite:sqlite:3.0.0",
                                   "cpe:/a:sqlite:sqlite"
                               ],
                               error_values=["", "\n"])

  def test_description_validation(self):
    self._run_field_validation(
        validator=fields.DescriptionField.validate,
        valid_values=[
            "This dependency is required to:\n"
            "    * foo\n"
            "    * bar", "One-line short description"
        ],
        error_values=["", "\n"],
    )

  def test_local_modifications_validation(self):
    self._run_field_validation(
        validator=fields.LocalModificationsField.validate,
        valid_values=[
            "It is the same code in the source repo, but:\n"
            "    * there is an added README.chromium file\n"
            "    * the function 'foo' was renamed to 'bar' for clarity",
            "One-line short list of modifications"
        ],
        error_values=["", "\n"],
    )


if __name__ == "__main__":
  unittest.main()
