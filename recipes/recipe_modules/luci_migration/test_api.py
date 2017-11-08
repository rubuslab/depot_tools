# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class LuciMigrationTestApi(recipe_test_api.RecipeTestApi):
  def __call__(self, is_luci):
    assert isinstance(is_luci, bool), '%r (%s)' % (is_luci, type(is_luci))
    ret = self.test(None)
    ret.properties.update(**{
      '$depot_tools/luci_migration': {
        'is_luci': is_luci,
      },
    })
    return ret
