#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
import re
import os
import sys
from typing import Dict, List, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata import fields
from metadata.util import ValidationResult, ValidationError

DEPENDENCY_DIVIDER = re.compile("-{20} DEPENDENCY DIVIDER -{20}")
FIELD_DELIMITER = ":"
FIELD_DECLARATION = re.compile(
    "^({}){}".format("|".join(fields.KNOWN_FIELD_NAMES), FIELD_DELIMITER),
    re.IGNORECASE,
)


class Metadatum(object):
  def __init__(self, field_label, value):
    self.field_label = field_label
    self.value = value.strip()


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

  def get_entries(self):
    return list(self._entries)

  @staticmethod
  def _process_entries(
      entries: List[Metadatum]) -> Tuple[Dict[str, str], Dict[str, int]]:
    data = {}
    field_occurrences = defaultdict(int)
    for metadatum in entries:
      field = fields.get_field(metadatum.field_label)
      if field:
        field_name = field.NAME
        data[field_name] = metadatum.value
        field_occurrences[field_name] += 1

    return data, field_occurrences

  def assess_required_fields(self) -> Set[fields.MetadataField]:
    required = set(self._MANDATORY_FIELDS)

    # The date and revision are required if the version has not been specified.
    version = self._data.get(fields.VersionField.NAME)
    if version and fields.VersionField.is_unknown(version):
      required.add(fields.DateField.NAME)
      required.add(fields.RevisionField.NAME)

    is_shipped = fields.is_yes(self._data.get(fields.ShippedField.NAME))

    # A license file is required if the dependency is shipped.
    if is_shipped:
      required.add(fields.LicenseFileField.NAME)

    # License compatibility with Android must be set of the package is shipped
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

  def validate(self) -> List[ValidationResult]:
    results = []

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

    return results


def parse_metadata_file(filepath: str) -> List[Metadata]:
  """Reads the metadata in the given file.

    Args:
        filepath: path to metadata file.

    Returns:
        all the metadata for each dependency described in the file.
    """
  with open(filepath, "r") as f:
    lines = f.readlines()

  all_metadata = []
  dependency_entries = []
  field_label = None
  value = ""
  for line in lines:
    if DEPENDENCY_DIVIDER.match(line):
      all_metadata.append(Metadata(dependency_entries))
      dependency_entries = []

    elif FIELD_DECLARATION.match(line):
      if field_label:
        dependency_entries.append(Metadatum(field_label, value))
        field_label = None

      field_label, line_value = line.split(FIELD_DELIMITER, 1)
      field = fields.get_field(field_label)
      if field and field.ONE_LINER:
        dependency_entries.append(Metadatum(field_label, line_value))
        field_label = None
      else:
        value = line_value

    elif field_label:
      value += line

  if field_label:
    dependency_entries.append(Metadatum(field_label, value))

  if dependency_entries:
    all_metadata.append(Metadata(dependency_entries))

  return all_metadata
