#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata import fields
from metadata.model import Metadatum, Metadata

DEPENDENCY_DIVIDER = re.compile(r"-{20} DEPENDENCY DIVIDER -{20}")
FIELD_DELIMITER = ":"
FIELD_DECLARATION = re.compile(
    "^\s*({})\s*{}".format("|".join(fields.KNOWN_FIELD_NAMES), FIELD_DELIMITER),
    re.IGNORECASE,
)


def parse_file(filepath: str) -> List[Metadata]:
  """Reads and parses the metadata in the given file.

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
      if field_label:
        dependency_entries.append(Metadatum(field_label, value))
        field_label = None
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
