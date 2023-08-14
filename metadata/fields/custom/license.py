#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re
import sys
from typing import List, Union

_THIS_DIR = os.path.abspath(os.path.dirname(__file__))
_ROOT_DIR = os.path.abspath(os.path.join(_THIS_DIR, "..", "..", ".."))

sys.path.insert(0, _ROOT_DIR)

import metadata.fields.types as field_types
import metadata.fields.util as util
import metadata.validation_result as vr

# The delimiter used to separate multiple license types.
_VALUE_DELIMITER = ";"

# Copied from ANDROID_ALLOWED_LICENSES in
# https://chromium.googlesource.com/chromium/src/+/refs/heads/main/third_party/PRESUBMIT.py
_ANDROID_ALLOWED_LICENSES = [
    "A(pple )?PSL 2(\.0)?",
    "Android Software Development Kit License",
    "Apache( License)?,?( Version)? 2(\.0)?",
    "(New )?([23]-Clause )?BSD( [23]-Clause)?( with advertising clause)?",
    "GNU Lesser Public License",
    "L?GPL ?v?2(\.[01])?( or later)?( with the classpath exception)?",
    "(The )?MIT(/X11)?(-like)?( License)?",
    "MPL 1\.1 ?/ ?GPL 2(\.0)? ?/ ?LGPL 2\.1",
    "MPL 2(\.0)?",
    "Microsoft Limited Public License",
    "Microsoft Permissive License",
    "Public Domain",
    "Python",
    "SIL Open Font License, Version 1.1",
    "SGI Free Software License B",
    "Unicode, Inc. License",
    "University of Illinois\/NCSA Open Source",
    "X11",
    "Zlib",
]
_PATTERN_LICENSE_ALLOWED = re.compile(
    "^({})$".format("|".join(_ANDROID_ALLOWED_LICENSES)),
    re.IGNORECASE,
)


def split_license_value(value: str) -> List[str]:
  """Process the raw value of a license field into separate licenses."""
  # Some licenses have commas within their name, so check the entire value
  # first, before splitting by comma.
  if is_license_allowlisted(value):
    return [value]

  licenses = re.split(f" and | or | / |{_VALUE_DELIMITER}", value)
  return [license.strip() for license in licenses]


def is_license_allowlisted(value: str) -> bool:
  """Returns whether the license is in the allowlist."""
  return util.matches(_PATTERN_LICENSE_ALLOWED, value)


class LicenseField(field_types.CustomField):
  """Custom field for the package's license type(s).

  e.g. Apache 2.0, MIT, BSD, Public Domain.
  """
  def __init__(self):
    super().__init__(name="License", one_liner=True)

  def validate(self, value: str) -> Union[vr.ValidationResult, None]:
    """Checks the given value consists of recognized license types.

    Note: this field supports multiple values.
    """
    not_allowlisted = []
    for license in split_license_value(value):
      if util.is_empty(license):
        return vr.ValidationError(
            f"{self._name} has an empty license type entry.")
      if not is_license_allowlisted(license):
        not_allowlisted.append(license)

    if not_allowlisted:
      template = ("{field_name} has license types not in the allowlist. If "
                  "there are multiple license types, separate them with a "
                  "'{delim}'. Invalid values: {values}.")
      message = template.format(field_name=self._name,
                                delim=_VALUE_DELIMITER,
                                values=util.quoted(not_allowlisted))
      return vr.ValidationWarning(message)

    if re.match(" (and|/|or) ", value):
      return vr.ValidationWarning(
          f"{self._name} should use '{_VALUE_DELIMITER}' to delimit values.")

    return None
