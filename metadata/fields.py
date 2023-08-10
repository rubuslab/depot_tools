#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
import os
import sys
from typing import List, Union

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from metadata.validation_result import ValidationResult, ValidationError, ValidationWarning

# The delimiter used for fields that support having multiple values.
VALUE_DELIMITER = ","

# Values and patterns for yes/no fields.
NO = "no"
YES = "yes"
PATTERN_LENIENT_NO = re.compile(f"^{NO}", re.IGNORECASE)
PATTERN_YES_OR_NO = re.compile(f"^({YES}|{NO})$", re.IGNORECASE)

# Pattern used to checxk for functionally empty fields.
PATTERN_ONLY_WHITESPACE = re.compile(r"^\s*$")

# Field-specific patterns.
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


class _MetadataField(object):
  # The name of the metadata field.
  NAME = ""

  # Whether the field should be specified on one line.
  ONE_LINER = True

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    raise NotImplementedError(f"{cls.NAME} field validation not defined")


class _FreeformTextMetadataField(_MetadataField):
  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} has an empty value", field=cls.NAME)
    return None


class NameField(_FreeformTextMetadataField):
  NAME = "Name"


class ShortNameField(_FreeformTextMetadataField):
  NAME = "Short Name"


class RevisionField(_FreeformTextMetadataField):
  NAME = "Revision"


class DescriptionField(_FreeformTextMetadataField):
  NAME = "Description"
  ONE_LINER = False


class LocalModificationsField(_FreeformTextMetadataField):
  NAME = "Local Modifications"
  ONE_LINER = False


class VersionField(_FreeformTextMetadataField):
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


class _YesNoMetadataField(_MetadataField):
  @staticmethod
  def is_no(value: str) -> bool:
    if value is None:
      return False

    return matches(PATTERN_LENIENT_NO, value)

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if value == YES or value == NO:
      return None

    if matches(PATTERN_YES_OR_NO, value):
      return ValidationWarning(
          f"{cls.NAME} is '{value}' - should be '{YES}' or '{NO}'",
          field=cls.NAME,
      )

    return ValidationError(
        f"{cls.NAME} is '{value}' - must be '{YES}' or '{NO}'",
        field=cls.NAME,
    )


class SecurityCriticalField(_YesNoMetadataField):
  NAME = "Security Critical"


class ShippedField(_YesNoMetadataField):
  NAME = "Shipped"


class LicenseAndroidCompatibleField(_YesNoMetadataField):
  NAME = "License Android Compatible"


class URLField(_MetadataField):
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
      return ValidationError(
          "{} had invalid values - must use protocol scheme in "
          "[http, https, ftp, git] and be comma-separated if there are multiple "
          "URLs. Invalid values: {}".format(
              cls.NAME,
              ", ".join(["'{}'".format(value) for value in invalid_values])),
          field=cls.NAME,
      )

    return None


class DateField(_MetadataField):
  NAME = "Date"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if not matches(PATTERN_DATE, value):
      return ValidationError(
          f"{cls.NAME} is '{value}' - must use format YYYY-MM-DD",
          field=cls.NAME,
      )
    return None


class LicenseField(_MetadataField):
  NAME = "License"

  @staticmethod
  def is_allowlisted(value: str):
    return matches(PATTERN_ALLOWED_LICENSE, value)

  @classmethod
  def process_license_value(cls, value: str) -> List[str]:
    # Some licenses have commas within their name, so check the entire value
    # first, before splitting by comma.
    if cls.is_allowlisted(value):
      return [value]

    licenses = re.split(f" and | or | / |{VALUE_DELIMITER}", value)
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


class LicenseFileField(_MetadataField):
  NAME = "License File"

  @classmethod
  def validate(cls, value: str) -> Union[ValidationResult, None]:
    if value == "NOT_SHIPPED":
      return ValidationWarning(
          f"{cls.NAME} has deprecated value NOT_SHIPPED "
          f"- use '{ShippedField.NAME}: {NO}' instead",
          field=cls.NAME)

    for license_file in value.split(VALUE_DELIMITER):
      if is_empty(license_file):
        return ValidationError(f"{cls.NAME} has an empty value", field=cls.NAME)

    return None

  @classmethod
  def validate_on_disk(cls, value: str, readme_dir: str,
                       chromium_src_dir: str) -> Union[ValidationResult, None]:
    if value == "NOT_SHIPPED":
      return ValidationWarning(
          f"{cls.NAME} has deprecated value NOT_SHIPPED "
          f"- use '{ShippedField.NAME}: {NO}' instead",
          field=cls.NAME)

    invalid_values = []
    for license_filename in value.split(VALUE_DELIMITER):
      license_filename = license_filename.strip()
      if license_filename.startswith("/"):
        license_filepath = os.path.join(
            chromium_src_dir, os.path.normpath(license_filename.lstrip("/")))
      else:
        license_filepath = os.path.join(readme_dir,
                                        os.path.normpath(license_filename))

      if not os.path.exists(license_filepath):
        invalid_values.append(license_filepath)

    if invalid_values:
      return ValidationError("{} field has file not found on disk: {}".format(
          cls.NAME, ", ".join(invalid_values)),
                             field=cls.NAME)


class CPEPrefixField(_MetadataField):
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


def get_field(label: str) -> Union[_MetadataField, None]:
  return FIELD_MAPPING.get(label.lower())
