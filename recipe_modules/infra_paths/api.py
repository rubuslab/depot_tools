# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class InfraPathsApi(recipe_api.RecipeApi):
  """infra_paths module is glue for design mistakes. It will be removed."""

  def initialize(self):
    path_config = self.m.properties.get('path_config', 'generic')
    self.m.path.set_config('infra_' + path_config)
