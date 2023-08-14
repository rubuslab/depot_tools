#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from typing import List

# Values and patterns for yes/no values.
YES = "yes"
NO = "no"
_PATTERN_LENIENT_YES = re.compile(r"^yes", re.IGNORECASE)
_PATTERN_LENIENT_NO = re.compile(r"^no", re.IGNORECASE)

# Common patterns for field values.
_PATTERN_UNKNOWN = re.compile(r"^unknown$", re.IGNORECASE)
_PATTERN_ONLY_WHITESPACE = re.compile(r"^\s*$")


def matches(pattern: re.Pattern, value: str) -> bool:
  """Returns whether the value matches the pattern."""
  return pattern.match(value) is not None


def is_empty(value: str) -> bool:
  """Returns whether the value is functionally empty."""
  return matches(_PATTERN_ONLY_WHITESPACE, value)


def is_unknown(value: str) -> bool:
  """Returns whether the value is 'unknown' (case insensitive)."""
  return matches(_PATTERN_UNKNOWN, value)


def is_yes(value: str) -> bool:
  """Returns whether the value starts with 'yes' (case insensitive)."""
  return matches(_PATTERN_LENIENT_YES, value)


def is_no(value: str) -> bool:
  """Returns whether the value starts with 'no' (case insensitive)."""
  return matches(_PATTERN_LENIENT_NO, value)


def quoted(values: List[str]) -> str:
  """Returns a string of the given values, each being individually quoted."""
  return ", ".join([f"'{entry}'" for entry in values])
