#!/usr/bin/env python3
# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re
from typing import List, Union

from metadata.util import ValidationResult, ValidationError, ValidationWarning

FIELD_DELIMITER = ","
NO = "no"
YES = "yes"

PATTERN_ONLY_WHITESPACE = re.compile(r"^\s*$")
PATTERN_YES_OR_NO = re.compile(f"^\s*({YES}|{NO})\s*$")

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


def is_yes_or_no(value: str) -> bool:
  return matches(PATTERN_YES_OR_NO, value)


def is_allowed_license(value: str) -> bool:
  return matches(PATTERN_ALLOWED_LICENSE, value)


class MetadataField(object):
  # The name of the metadata field.
  NAME = ""

  # Whether the field should be specified on one line.
  ONE_LINER = True

  # Whether the field supports multiple values.
  MULTIVALUE = False

  @staticmethod
  def is_required(metadata: dict) -> bool:
    return True

  @classmethod
  def validate(cls, metadata) -> List[ValidationResult]:
    results = []

    if cls.NAME not in metadata:
      if cls.is_required(metadata):
        results.append(ValidationError(f"{cls.NAME} is missing",
                                       field=cls.NAME))
      return results

    raw_value = metadata.get(cls.NAME)
    if cls.MULTIVALUE:
      field_values = raw_value.split(FIELD_DELIMITER)
    else:
      field_values = [raw_value]

    for value in field_values:
      result = cls.validate_single_value(value)
      if result:
        results.append(result)

    return results

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    raise NotImplementedError()


class NameField(MetadataField):
  NAME = "Name"

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)
    return None


class ShortNameField(MetadataField):
  NAME = "Short Name"

  @staticmethod
  def is_required(metadata: dict) -> bool:
    return False

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationWarning(f"{cls.NAME} is declared but has no value",
                               field=cls.NAME)
    return None


class URLField(MetadataField):
  NAME = "URL"
  ONE_LINER = False
  MULTIVALUE = True

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)
    return None


class VersionField(MetadataField):
  NAME = "Version"

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)
    return None


class DateField(MetadataField):
  NAME = "Date"

  @staticmethod
  def is_required(metadata: dict) -> bool:
    version = metadata.get(VersionField.NAME)
    revision = metadata.get(RevisionField.NAME)
    return (version == "N/A" or version == "0") and revision is None

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)
    return None


class RevisionField(MetadataField):
  NAME = "Revision"

  @staticmethod
  def is_required(metadata: dict) -> bool:
    version = metadata.get(VersionField.NAME)
    date = metadata.get(DateField.NAME)
    return (version == "N/A" or version == "0") and date is None

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)
    return None


class LicenseField(MetadataField):
  NAME = "License"
  MULTIVALUE = True

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)

    if not is_allowed_license(value):
      return ValidationError(
          f"license type '{value}' has not been allowlisted",
          field=cls.NAME,
      )

    return None


class LicenseFileField(MetadataField):
  NAME = "License File"
  MULTIVALUE = True

  @staticmethod
  def is_required(metadata: dict) -> bool:
    shipped = metadata.get(ShippedField.NAME)
    return shipped == YES

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)

    # TODO: check existence of filepath
    return None


class SecurityCriticalField(MetadataField):
  NAME = "Security Critical"

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if not is_yes_or_no(value):
      return ValidationError(
          f"{cls.NAME} is '{value}' - must be either '{YES}' or '{NO}'",
          field=cls.NAME,
      )

    return None


class ShippedField(MetadataField):
  NAME = "Shipped"

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if not is_yes_or_no(value):
      return ValidationError(
          f"{cls.NAME} is '{value}' - must be either '{YES}' or '{NO}'",
          field=cls.NAME,
      )

    return None


class LicenseAndroidCompatibleField(MetadataField):
  NAME = "License Android Compatible"

  @staticmethod
  def is_required(metadata: dict) -> bool:
    shipped = metadata.get(ShippedField.NAME)
    license = metadata.get(LicenseField.NAME)

    if shipped == YES:
      allowed_license = is_allowed_license(license) if license else False
      return not allowed_license

    return False

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if not is_yes_or_no(value):
      return ValidationError(
          f"{cls.NAME} is '{value}' - must be either '{YES}' or '{NO}'",
          field=cls.NAME,
      )

    return None


class CPEPrefixField(MetadataField):
  NAME = "CPEPrefix"

  @staticmethod
  def is_required(metadata: dict) -> bool:
    return False

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationError(f"{cls.NAME} is declared but has no value",
                             field=cls.NAME)

    return None


class DescriptionField(MetadataField):
  NAME = "Description"
  ONE_LINER = False

  @staticmethod
  def is_required(metadata: dict) -> bool:
    return False

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationWarning(f"{cls.NAME} is declared but has no value",
                               field=cls.NAME)

    return None


class LocalModificationsField(MetadataField):
  NAME = "Local Modifications"
  ONE_LINER = False

  @staticmethod
  def is_required(metadata: dict) -> bool:
    return False

  @classmethod
  def validate_single_value(cls, value: str) -> Union[ValidationResult, None]:
    if is_empty(value):
      return ValidationWarning(f"{cls.NAME} is declared but has no value",
                               field=cls.NAME)

    return None


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

FIELDS_BY_NAME = {field.NAME.lower(): field for field in KNOWN_FIELDS}
