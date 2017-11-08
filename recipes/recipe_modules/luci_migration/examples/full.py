# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json

DEPS = [
  'depot_tools/luci_migration',
  'recipe_engine/step',
]


def RunSteps(api):
  api.step('show properties', [])
  api.step.active_result.presentation.logs['result'] = [
    'is_luci: %r' % (api.luci_migration.is_luci,),
    'is_prod: %r' % (api.luci_migration.is_prod,),
  ]


def GenTests(api):
  yield api.test('default')

  for is_luci in [True, False]:
    for is_prod in [True, False]:
      yield (
          api.test('stack_%s-prod_%s' % (
              ('luci' if is_luci else 'buildbot'), is_prod)) +
          api.luci_migration(is_luci=is_luci, is_prod=is_prod)
      )
