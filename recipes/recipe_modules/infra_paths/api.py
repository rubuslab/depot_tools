# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class InfraPathsApi(recipe_api.RecipeApi):
  """infra_paths module is glue for design mistakes. It will be removed."""

  def initialize(self):
    path_config = self.m.properties.get('path_config')
    if path_config:
      # TODO(phajdan.jr): remove dupes from the engine and delete infra_ prefix.
      self.m.path.set_config('infra_' + path_config)
    else:
      self.m.path.set_config('path_base')

  @property
  def default_git_cache_dir(self):
    """Returns the location of the default git cache directory.

    This property should be used instead of using path['git_cache'] directly.

    It returns git_cache path if it is defined (Buildbot world), otherwise
    uses the more generic [CACHE]/git path (LUCI world).
    """
    try:
      return self.m.path['git_cache']
    except KeyError:
      return self.m.path['cache'].join('git')

  def all_builder_cache_dirs(self):
    """Returns (set of Path): A set of all possible "builder_cache" directories.

    This implements the superset of all configs defined in "path_config.py"
    to create a list of all possible "builder_cache" directory names for the
    current platform.
    """
    # Collect a list of all possible "cache" path values for this platform.
    all_cache_dirs = []

    # infra_buildbot
    all_cache_dirs.append(self.m.path['infra_b_dir'].join(
        'build', 'slave', 'cache'))

    # infra_kitchen
    all_cache_dirs.append(self.m.path['infra_kitchen_cache'].join('b'))

    # infra_generic
    all_cache_dirs.append(self.m.path['cache'].join('builder'))

    return all_cache_dirs
