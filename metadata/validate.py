#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
from typing import List, Tuple

_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
# The repo's root directory.
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, ".."))

# Add the repo's root directory for clearer imports.
sys.path.insert(0, _ROOT_DIR)

import metadata.parse
import metadata.validation_result as vr


def validate_content(content: str, source_file_dir: str,
                     repo_root_dir: str) -> List[vr.ValidationResult]:
  """Validate the content as a metadata file.

  Args:
    content: the entire content of a file to be validated as a metadata file.
    source_file_dir: the directory of the metadata file that the license file
                     value is from; this is needed to construct file paths to
                     license files.
    repo_root_dir: the repository's root directory; this is needed to construct
                   file paths to license files.

  Returns: the validation results.
  """
  results = []
  dependencies = metadata.parse.parse_content(content)
  if not dependencies:
    result = vr.ValidationError("No dependency metadata found")
    result.set_tag("reason", "no metadata")
    return [result]

  for dependency in dependencies:
    dependency_results = dependency.validate(source_file_dir=source_file_dir,
                                             repo_root_dir=repo_root_dir)
    results.extend(dependency_results)
  return results


def check_content(content: str, source_file_dir: str,
                  repo_root_dir: str) -> Tuple[List[str], List[str]]:
  """Run metadata validation on the given content, and return all validation
  errors and validation warnings.

  Args:
    content: the entire content of a file to be validated as a metadata file.
    source_file_dir: the directory of the metadata file that the license file
                     value is from; this is needed to construct file paths to
                     license files.
    repo_root_dir: the repository's root directory; this is needed to construct
                   file paths to license files.

  Returns:
    error_messages: the fatal validation issues present in the file;
                    i.e. presubmit should fail.
    warning_messages: the non-fatal validation issues present in the file;
                      i.e. presubmit should still pass.
  """
  results = validate_content(content=content,
                             source_file_dir=source_file_dir,
                             repo_root_dir=repo_root_dir)

  error_messages = []
  warning_messages = []
  for result in results:
    message = result.get_message(width=60)

    # TODO(aredulla): Actually distinguish between validation errors and
    # warnings. The quality of metadata is currently being uplifted, but is not
    # yet guaranteed to pass validation. So for now, all validation results will
    # be returned as warnings so CLs are not blocked by invalid metadata in
    # presubmits yet. Bug: b/285453019.
    # if result.is_fatal():
    #   error_messages.append(message)
    # else:
    warning_messages.append(message)

  return error_messages, warning_messages


def validate_file(filepath: str,
                  repo_root_dir: str) -> List[vr.ValidationResult]:
  """Validate the file

  Args:
    filepath: the path to a metadata file,
              e.g. "/chromium/src/third_party/libname/README.chromium"
    repo_root_dir: the repository's root directory; this is needed to construct
                   file paths to license files.
  """
  content = metadata.parse.read_file(filepath)

  # Get the directory the metadata file is in.
  source_file_dir = os.path.dirname(filepath)

  return validate_content(content=content,
                          source_file_dir=source_file_dir,
                          repo_root_dir=repo_root_dir)
