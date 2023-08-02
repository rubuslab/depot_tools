#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import argparse
import os
from typing import List

import metadata.validator as validator


def find_readmes(root: str) -> List[str]:
  readmes = []
  for item in os.listdir(root):
    full_path = os.path.join(root, item)
    if item == "README.chromium":
      readmes.append(full_path)
    elif os.path.isdir(full_path):
      readmes.extend(find_readmes(full_path))

  return readmes


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
  try:
    config = parse_args()

    src_dir = config.chromium_src_dir
    readmes = find_readmes(src_dir)
    file_count = len(readmes)
    print(f"Found {file_count} README.chromium files")
    results = validator.validate_metadata_files(readmes)

    invalid_file_count = 0
    for filepath, file_results in results.items():
      invalid = False
      if file_results:
        print(f"\n{len(file_results)} problem(s) in {filepath}:")
        for result in file_results:
          print(f"    {result}")
          if result.is_fatal():
            invalid = True
      if invalid:
        invalid_file_count += 1

    print(f"\n\nDone. {invalid_file_count} / {file_count} READMEs "
          "had validation errors.")
  except Exception as e:
    print("Error:", e)
    raise

  return 0


if __name__ == "__main__":
  main()
