#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import sys
from typing import Union

_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))

sys.path.insert(0, _ROOT_DIR)

import metadata.fields.util as util
import metadata.validation_result as vr

# Patterns for yes/no metadata field.
_PATTERN_LENIENT_YES_OR_NO = re.compile(r"^(yes|no)", re.IGNORECASE)
_PATTERN_YES_OR_NO = re.compile(r"^(yes|no)$", re.IGNORECASE)


class MetadataField:
  """Base class for all metadata fields."""
  def __init__(self, name: str, one_liner: bool = True):
    self._name = name
    self._one_liner = one_liner

  def get_name(self):
    return self._name

  def validate(self, value: str) -> Union[vr.ValidationResult, None]:
    """Checks the given value is acceptable for the field."""
    # All values are valid.
    return None


class FreeformTextField(MetadataField):
  """Field where the value is freeform text."""
  def validate(self, value: str) -> Union[vr.ValidationResult, None]:
    """Checks the given value has at least one non-whitespace character."""
    if util.is_empty(value):
      return vr.ValidationError(f"{self._name} is empty.")

    return None


class YesNoField(MetadataField):
  """Field where the value must be yes or no."""
  def __init__(self, name: str):
    super().__init__(name=name, one_liner=True)

  def validate(self, value: str) -> Union[vr.ValidationResult, None]:
    """Checks the given value is either yes or no."""
    if util.matches(_PATTERN_YES_OR_NO, value):
      return None

    if util.matches(_PATTERN_LENIENT_YES_OR_NO, value):
      return vr.ValidationWarning(
          f"{self._name} is '{value}' - should be simply {util.YES} or {util.NO}."
      )

    return vr.ValidationError(
        f"{self._name} is '{value}' - must be {util.YES} or {util.NO}.")


class CustomField(MetadataField):
  """Base class for custom metadata fields. Raises a NotImplementedError
    if the validate method is not overwritten.
    """
  def validate(self, value: str):
    raise NotImplementedError(f"{self._name} field validation not defined.")
