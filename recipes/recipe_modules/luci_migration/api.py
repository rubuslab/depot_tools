# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class LuciMigrationApi(recipe_api.RecipeApi):
  """This module assists in migrating builders from Buildbot to pure LUCI stack.

  Finishing migration means you no longer depend on this module.

  Usage:

      1. Add the "migrating_to_luci:true" to recipe properties of a builder in
      your cr-buildbucket.cfg.

              bucket {
                ...
                builders{
                  name: "this builder is on luci"
                  ...
                  recipe{
                    ...
                    properties_j: "$depot_tools/luci_migration:{\"on_luci\": true}"
                }
                ...
              }

      2. In your recipe, you may add conditional execution:

              if api.luci_migration.on_luci:
                do_luci_specific_stuff()
              else:
                do_buildbot_stuff()
  """

  def __init__(self, migration_properties, **kwargs):
    super(LuciMigrationApi, self).__init__(**kwargs)
    self._migration_properties = migration_properties

  @property
  def on_luci(self):
    """True if runs on LUCI stack."""
    return bool(self._migration_properties.get('on_luci', False))
