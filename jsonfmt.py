#!/usr/bin/env python3
# Copyright 2022 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import sys


def _read_file(file_path):
  with open(file_path) as file:
    return file.read()


def _format_json(file_data):
  file_data_json = json.loads(file_data)
  return json.dumps(file_data_json, indent=2) + '\n'


def _save_file(file_path, formatted_data):
  with open(file_path, mode='w') as file:
    file.write(formatted_data)


def format_json(json_files, check=False):
  """ Formats any JSON files provided

    Returns false if the check failed
    """

  for file_path in json_files:
    before = _read_file(file_path)
    after = _format_json(before)

    if after != before:
      if check:
        return False

      _save_file(file_path, after)

  return True


def main(json_files):
  if format_json(json_files):
    print('Formatted files: %s' % json_files)
  else:
    sys.stderr.write('Failed to format JSON files\n')
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv[1:])
