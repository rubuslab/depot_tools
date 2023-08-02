#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import defaultdict
from typing import Dict, List

from metadata.util import ValidationResult, ValidationError
import metadata.fields as fields
from metadata.parse import read_metadata


def validate_metadata_file(filepath: str) -> List[ValidationResult]:
  """Checks the third party metadata in the given file
       satisfies all Chromium metadata validation rules.

       See go/chromium-readme-validation-rules
    """
  dependencies = read_metadata(filepath)

  file_results = []
  for raw_metadata in dependencies:
    metadata = {}
    field_occurrences = defaultdict(int)
    for field_name, raw_value in raw_metadata:
      field_occurrences[field_name] += 1
      metadata[field_name] = raw_value

    results = [
        ValidationError(f"Field '{field_name}' was specified {n} times")
        for field_name, n in field_occurrences.items() if n > 1
    ]
    for field in fields.KNOWN_FIELDS:
      results.extend(field.validate(metadata))

    file_results.extend(results)

  return file_results


def validate_metadata_files(
    filepaths: List[str]) -> Dict[str, List[ValidationResult]]:
  results_per_file = {}
  for path in filepaths:
    results_per_file[path] = validate_metadata_file(path)

  return results_per_file
