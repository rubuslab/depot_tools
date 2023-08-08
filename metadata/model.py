#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import os
import sys
from typing import Dict, List, Set, Tuple, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata import fields
from metadata.validation_result import ValidationResult, ValidationError, ValidationWarning


class Metadatum(object):
  def __init__(self, field_label, value):
    self.field_label = field_label
    self.value = value.strip()

  def __eq__(self, other):
    if isinstance(other, Metadatum):
      return (self.field_label == other.field_label
              and self.value == other.value)
    return False

  def __str__(self):
    return f'"{self.field_label}"="{self.value}"'

  def __repr__(self) -> str:
    return f"Metadatum({str(self)})"

  def validate_field_label(self) -> Union[ValidationResult, None]:
    if self.field_label in fields.KNOWN_FIELD_NAMES:
      return None

    if self.field_label.strip() != self.field_label:
      return ValidationError(f"Invalid field label '{self.field_label}' - "
                             "remove leading & trailing whitespace")

    field = fields.get_field(self.field_label)
    if field:
      # Casing is off.
      message = (f"Field label '{self.field_label}' should be '{field.NAME}' - "
                 "check case")
      return ValidationWarning(message)

    return ValidationError(f"Unknown field label '{self.field_label}'")


class Metadata(object):
  _MANDATORY_FIELDS = {
      fields.NameField.NAME,
      fields.URLField.NAME,
      fields.VersionField.NAME,
      fields.LicenseField.NAME,
      fields.SecurityCriticalField.NAME,
      fields.ShippedField.NAME,
  }

  def __init__(self, entries: List[Metadatum]):
    self._entries = entries
    self._data, self._field_occurrences = self._process_entries(self._entries)

  def __eq__(self, other):
    if isinstance(other, Metadata):
      return (self._entries == other._entries)
    return False

  def __str__(self):
    return ",\n".join([str(entry) for entry in self._entries])

  def __repr__(self):
    return f"Metadata({str(self)})"

  def get_entries(self):
    return list(self._entries)

  @staticmethod
  def _process_entries(
      entries: List[Metadatum]) -> Tuple[Dict[str, str], Dict[str, int]]:
    data = {}
    field_occurrences = defaultdict(int)
    for metadatum in entries:
      field = fields.get_field(metadatum.field_label.strip())
      if field:
        field_name = field.NAME
        data[field_name] = metadatum.value
        field_occurrences[field_name] += 1

    return data, field_occurrences

  def assess_required_fields(self) -> Set[fields._MetadataField]:
    required = set(self._MANDATORY_FIELDS)

    # The date and revision are required if the version has not been specified.
    version = self._data.get(fields.VersionField.NAME)
    if version and fields.VersionField.is_unknown(version):
      required.add(fields.DateField.NAME)
      required.add(fields.RevisionField.NAME)

    # Assume the dependency is shipped if not specified.
    is_shipped = True
    shipped_value = self._data.get(fields.ShippedField.NAME)
    if shipped_value and fields.ShippedField.is_no(shipped_value):
      is_shipped = False

    # A license file is required if the dependency is shipped.
    if is_shipped:
      required.add(fields.LicenseFileField.NAME)

    # License compatibility with Android must be set if the package is shipped
    # and the license is not in the allowlist.
    license_entry = self._data.get(fields.LicenseField.NAME)
    if is_shipped and license_entry:
      licenses = fields.LicenseField.process_license_value(license_entry)
      has_allowlisted = False
      for license in licenses:
        if fields.LicenseField.is_allowlisted(license):
          has_allowlisted = True
          break

      if not has_allowlisted:
        required.add(fields.LicenseAndroidCompatibleField.NAME)

    return required

  def validate(self, readme_dir: str,
               chromium_src_dir: str) -> List[ValidationResult]:
    results = []

    # Check field labels.
    for entry in self._entries:
      result = entry.validate_field_label()
      if result:
        results.append(result)

    # Check for duplicate fields.
    repeated_fields = [
        f"{field} ({count})"
        for field, count in self._field_occurrences.items() if count > 1
    ]
    if repeated_fields:
      results.append(
          ValidationError("Multiple entries for the same field: "
                          ", ".join(repeated_fields)))

    # Check required fields are present.
    required_fields = self.assess_required_fields()
    for field_name in required_fields:
      if field_name not in self._data:
        results.append(
            ValidationError(
                f"Required field '{field_name}' is missing",
                field=field_name,
            ))

    # Validate values for all present fields.
    for field_name, value in self._data.items():
      field_result = fields.get_field(field_name).validate(value)
      if field_result:
        results.append(field_result)

    # Check existence of the license file(s) on disk.
    license_file = self._data.get(fields.LicenseFileField.NAME)
    if license_file is not None:
      result = fields.LicenseFileField.validate_on_disk(
          value=license_file,
          readme_dir=readme_dir,
          chromium_src_dir=chromium_src_dir,
      )
      if result:
        results.append(result)

    return results
