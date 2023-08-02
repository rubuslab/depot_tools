#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import namedtuple
import re
from typing import List

import metadata.fields as fields

DEPENDENCY_DIVIDER = re.compile("-{20} DEPENDENCY DIVIDER -{20}")
FIELD_DELIMITER = ":"
FIELD_DECLARATION = re.compile(
    "^({}){}".format("|".join(fields.FIELDS_BY_NAME.keys()), FIELD_DELIMITER),
    re.IGNORECASE,
)

FieldEntry = namedtuple('FieldEntry', ['name', 'value'])


def read_metadata(filepath: str) -> List[List[FieldEntry]]:
  """Reads the metadata in the given file.

    Args:
        filepath: path to metadata file.

    Returns:
        all the metadata in the file, as a list of lists. Each list element
        is a list of the metadata for a single dependency.
    """
  with open(filepath, "r") as f:
    lines = f.readlines()

  dependencies = []
  metadata = []
  field_name = None
  value = ""
  for line in lines:
    if DEPENDENCY_DIVIDER.match(line):
      dependencies.append(metadata)
      metadata = []

    elif FIELD_DECLARATION.match(line):
      if field_name:
        metadata.append(FieldEntry(field_name, value))
        field_name = None

      field_label, line_value = line.split(FIELD_DELIMITER, 1)
      field = fields.FIELDS_BY_NAME[field_label.lower()]
      if field.ONE_LINER:
        metadata.append(FieldEntry(field.NAME, line_value.strip()))
      else:
        field_name = field.NAME
        value = line_value

    elif field_name:
      value += line

  if field_name:
    metadata.append(FieldEntry(field_name, value))

  if metadata:
    dependencies.append(metadata)

  return dependencies
