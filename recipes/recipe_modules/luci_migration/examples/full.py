# Copyright 2016 The Chromium Authors. All rights reserved.
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
    'on_luci: %r' % (api.luci_migration.on_luci,),
  ]


def GenTests(api):
  yield api.test('default')

  for on_luci in [True, False]:
    yield (
        api.test('stack_%s' % ('luci' if on_luci else 'buildbot')) +
        api.luci_migration(on_luci=on_luci)
    )
