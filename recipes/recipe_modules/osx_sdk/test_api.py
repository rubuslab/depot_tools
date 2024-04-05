# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import re

from recipe_engine import recipe_test_api


class OSXSDKTestApi(recipe_test_api.RecipeTestApi):
  # In tests, this will be the version that we simulate macOS to be.
  DEFAULT_MACOS_VERSION = '14.4'

  def osx_version(self, major_minor: str = DEFAULT_MACOS_VERSION) -> recipe_test_api.TestData:
    """Mock the macOS Major.Minor version that osx_sdk will use to pick the
    Xcode SDK version from it's internal table.

    This will only be used if the recipe does not explicitly select an SDK
    version via the osx_sdk properties.
    """
    if not re.match(r'^\d+(\.\d+){1,2}$', major_minor):
      raise ValueError(f'Expected Major.Minor[.Patch] (e.g. 14.4), got {major_minor=}')

    return self.step_data(
        'find macOS version',
        stdout=self.m.raw_io.output_text(major_minor))
