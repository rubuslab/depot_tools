#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
from collections import defaultdict
import os
import sys
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata.metadata import parse_metadata_file
from metadata.util import find_readmes, ValidationResult, ValidationError


def validate_file(filepath: str) -> List[ValidationResult]:
  """Checks the third party metadata in the given file
       satisfies all Chromium metadata validation rules.

       See go/chromium-readme-validation-rules
  """
  results = []
  for dependency_metadata in parse_metadata_file(filepath):
    dependency_results = dependency_metadata.validate()
    if dependency_results:
      results.extend(dependency_results)

  return results


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  chromium_src_dir = parser.add_argument(
      "chromium_src_dir",
      help=("The path to the directory for the Chromium root repository;"
            " this should end with '/src'."),
  )

  args = parser.parse_args()

  # Validate chromium/src directory exists
  src_dir = args.chromium_src_dir
  if not os.path.exists(src_dir) or not os.path.isdir(src_dir):
    raise argparse.ArgumentError(
        chromium_src_dir,
        f"Invalid chromium/src directory '{src_dir}' - not found",
    )

  return args


def main() -> None:
  config = parse_args()

  src_dir = config.chromium_src_dir
  readmes = find_readmes(src_dir)
  file_count = len(readmes)
  print(f"Found {file_count} README.chromium files")

  invalid_file_count = 0
  field_issues = defaultdict(set)
  for filepath in readmes:
    file_results = validate_file(filepath)
    invalid = False
    if file_results:
      print(f"\n{len(file_results)} problem(s) in {filepath}:")
      for result in file_results:
        print(f"    {result}")
        if result.is_fatal():
          invalid = True
        field_tag = result.get_tag("field")
        if field_tag:
          field_issues[field_tag].add(str(result))

    if invalid:
      invalid_file_count += 1

  print("\n\nField issues:")
  for field, issues in field_issues.items():
    print(f"{field}: {len(issues)}")
    for issue in issues:
      print(f"    {issue}")

  print(f"\n\nDone. {invalid_file_count} / {file_count} READMEs "
        "had validation errors.")


if __name__ == "__main__":
  main()
