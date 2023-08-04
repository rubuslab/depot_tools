#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import os
import sys
from typing import List, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata.util import ValidationResult, ValidationError, ValidationWarning

VALUE_DELIMITER = ","
NO = "no"
YES = "yes"

PATTERN_ONLY_WHITESPACE = re.compile(r"^\s*$")
PATTERN_LENIENT_YES = re.compile(f"^{YES}$", re.IGNORECASE)
PATTERN_LENIENT_YES_OR_NO = re.compile(f"^({YES}|{NO})$", re.IGNORECASE)
PATTERN_ALLOWED_URLS = re.compile(r"^(https?|ftp|git):\/\/\S+$")
PATTERN_DATE = re.compile(r"^\d{4}-(0|1)\d-[0-3]\d$")
PATTERN_CPE_PREFIX = re.compile(r"^cpe:/.+:.+:.+(:.+)*$")

ALLOWED_LICENSES = [
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
PATTERN_ALLOWED_LICENSE = re.compile(
    "^({})$".format("|".join(ALLOWED_LICENSES)),
    re.IGNORECASE,
)


def matches(pattern: re.Pattern, value: str) -> bool:
  return pattern.match(value) is not None


def is_empty(value: str) -> bool:
  return matches(PATTERN_ONLY_WHITESPACE, value)


def is_yes(value: Union[str, None]) -> bool:
  if value is None:
    return False

  return matches(PATTERN_LENIENT_YES, value)


def validate_yes_or_no_field(field_name: str,
                             value: str) -> Union[ValidationResult, None]:
  if value == YES or value == NO:
    return None

  if matches(PATTERN_LENIENT_YES_OR_NO, value):
    return ValidationWarning(
        f"{field_name} is '{value}' - should be '{YES}' or '{NO}'",
        field=field_name,
    )

  if is_empty(value):
    return ValidationError(f"{field_name} is empty", field=field_name)

  return ValidationError(
      f"{field_name} is '{value}' - must be '{YES}' or '{NO}'",
      field=field_name,
  )


class MetadataField(object):
  # The name of the metadata field.
  NAME = ""

  # Whether the field should be specified on one line.
  ONE_LINER = True

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} has an empty value", field=cls.NAME)
    return None


class NameField(MetadataField):
  NAME = "Name"


class ShortNameField(MetadataField):
  NAME = "Short Name"


class URLField(MetadataField):
  NAME = "URL"
  ONE_LINER = False

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if value == "This is the canonical public repository":
      return None

    invalid_values = []
    for url in value.split(VALUE_DELIMITER):
      url = url.strip()
      if not matches(PATTERN_ALLOWED_URLS, url):
        invalid_values.append(url)

    if invalid_values:
      return ValidationError("{} has unsupported protocol scheme: {}".format(
          cls.NAME,
          ", ".join(invalid_values),
      ))

    return None


class VersionField(MetadataField):
  NAME = "Version"

  @staticmethod
  def is_unknown(value: str) -> bool:
    return value == "N/A" or value == "0"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if value == "0":
      return ValidationWarning(f"{cls.NAME} is '{value}' - use 'N/A' instead",
                               field=cls.NAME)

    return super().validate(value)


class DateField(MetadataField):
  NAME = "Date"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if not matches(PATTERN_DATE, value):
      return ValidationError(
          f"{cls.NAME} is '{value}' - must use format YYYY-MM-DD",
          field=cls.NAME,
      )
    return None


class RevisionField(MetadataField):
  NAME = "Revision"


class LicenseField(MetadataField):
  NAME = "License"

  @staticmethod
  def is_allowlisted(value: str):
    return matches(PATTERN_ALLOWED_LICENSE, value)

  @classmethod
  def process_license_value(cls, value: str) -> List[str]:
    if cls.is_allowlisted(value):
      return [value]

    licenses = re.split(f' and | or | / |{VALUE_DELIMITER}', value)
    return [license.strip() for license in licenses]

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    invalid_values = []
    for license in cls.process_license_value(value):
      if not cls.is_allowlisted(license):
        invalid_values.append(license)

    if invalid_values:
      return ValidationError(
          "{} has type not in allowlist: {}".format(cls.NAME,
                                                    ", ".join(invalid_values)),
          field=cls.NAME,
      )

    if re.match(" (and|/|or) ", value):
      return ValidationWarning(
          f"{cls.NAME} should use '{VALUE_DELIMITER}' to delimit values",
          field=cls.NAME,
      )

    return None


class LicenseFileField(MetadataField):
  NAME = "License File"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    invalid_values = []
    for license_file in value.split(VALUE_DELIMITER):
      license_file = license_file.strip()
      if is_empty(license_file):
        invalid_values.append(license_file)

    if invalid_values:
      return ValidationError("{} has files not found: {}".format(
          cls.NAME,
          ", ".join(invalid_values),
          field=cls.NAME,
      ))

    return None


class SecurityCriticalField(MetadataField):
  NAME = "Security Critical"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    return validate_yes_or_no_field(cls.NAME, value)


class ShippedField(MetadataField):
  NAME = "Shipped"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    return validate_yes_or_no_field(cls.NAME, value)


class LicenseAndroidCompatibleField(MetadataField):
  NAME = "License Android Compatible"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    return validate_yes_or_no_field(cls.NAME, value)


class CPEPrefixField(MetadataField):
  NAME = "CPEPrefix"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if value == "unknown":
      return None

    if matches(PATTERN_CPE_PREFIX, value):
      return None

    return ValidationError(
        f"{cls.NAME} is '{value}' - must be either 'unknown' or in the form "
        "'cpe:/<part>:<vendor>:<product>[:<optional fields>]'",
        field=cls.NAME,
    )


class DescriptionField(MetadataField):
  NAME = "Description"
  ONE_LINER = False


class LocalModificationsField(MetadataField):
  NAME = "Local Modifications"
  ONE_LINER = False


KNOWN_FIELDS = (
    NameField,
    ShortNameField,
    URLField,
    VersionField,
    DateField,
    RevisionField,
    LicenseField,
    LicenseFileField,
    SecurityCriticalField,
    ShippedField,
    LicenseAndroidCompatibleField,
    CPEPrefixField,
    DescriptionField,
    LocalModificationsField,
)
KNOWN_FIELD_NAMES = {field.NAME for field in KNOWN_FIELDS}
FIELD_MAPPING = {field.NAME.lower(): field for field in KNOWN_FIELDS}


def get_field(label: str) -> Union[MetadataField, None]:
  return FIELD_MAPPING.get(label.lower())
