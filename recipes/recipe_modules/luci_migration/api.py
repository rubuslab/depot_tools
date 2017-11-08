# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class LuciMigrationApi(recipe_api.RecipeApi):
  """This module assists in migrating builders from Buildbot to pure LUCI stack.

  Finishing migration means you no longer depend on this module.
  """

  def __init__(self, migration_properties, **kwargs):
    super(LuciMigrationApi, self).__init__(**kwargs)
    self._migration_properties = migration_properties

  @property
  def is_luci(self):
    """True if runs on LUCI stack."""
    return bool(self._migration_properties.get('is_luci', False))

  @property
  def is_prod(self):
    """True if this builder is in production.

    Typical usage is to avoid doing steps with side-effects
    in LUCI builder during the migration and in buildbot after
    migration is complete.
    """
    return bool(self._migration_properties.get('is_prod', True))
