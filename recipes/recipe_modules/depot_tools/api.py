# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The `depot_tools` module provides safe functions to access paths within
the depot_tools repo."""

import contextlib

from recipe_engine import recipe_api

class DepotToolsApi(recipe_api.RecipeApi):
  @property
  def download_from_google_storage_path(self):
    return self.repo_resource('download_from_google_storage.py')

  @property
  def upload_to_google_storage_path(self):
    return self.repo_resource('upload_to_google_storage.py')

  @property
  def root(self):
    """Returns (Path): The "depot_tools" root directory."""
    return self.repo_resource()

  @property
  def cros_path(self):
    return self.repo_resource('cros')

  @property
  def gn_py_path(self):
    return self.repo_resource('gn.py')

  # TODO(dnj): Remove this once everything uses the "gsutil" recipe module
  # version.
  @property
  def gsutil_py_path(self):
    return self.repo_resource('gsutil.py')

  @property
  def ninja_path(self):
    ninja_exe = 'ninja.exe' if self.m.platform.is_win else 'ninja'
    return self.repo_resource(ninja_exe)

  @property
  def autoninja_path(self):
    autoninja = 'autoninja.bat' if self.m.platform.is_win else 'autoninja'
    return self.repo_resource(autoninja)

  @property
  def presubmit_support_py_path(self):
    return self.repo_resource('presubmit_support.py')

  @contextlib.contextmanager
  def on_path(self):
    """Use this context manager to put depot_tools on $PATH.

    Example:

    ```python
    with api.depot_tools.on_path():
      # run some steps
    ```
    """
    # Depot Tools intentionally doesn't self-update on bots, because it's part
    # of a recipe bundle (i.e. CIPD package). Attempting to do so will break
    # because the bundle is unpacked onto disk (intentionally) in read-only
    # mode.
    #
    # To add additional checked-in files to the recipe bundle, modify
    # .gitattributes and notate the files/file patterns with the `recipes`
    # attribute.
    #
    # If you need something more complicated than including checked-in files,
    # pull those explicitly:
    #   * (preferably) via dependencies in your project OR
    #   * (less perferably) via new steps in your recipe.
    #
    # (crbug.com/1090603)
    with self.m.context(
        **{'env_suffixes': {
            'PATH': [self.root],
            'DEPOT_TOOLS_UPDATE': '0'
        }}):
      yield
