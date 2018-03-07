# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine.config_types import Path


DEPS = [
  'deps2submodules',
  'gclient',
  'git',
  'recipe_engine/path',
]


def RunSteps(api):
  api.gclient.checkout(gclient_config=api.gclient.make_config('infra'))
  api.git.checkout('https://chromium.googlesource.com/infra/submods')
  api.deps2submodules(
    api.path['start_dir'].join('infra'), api.path['start_dir'].join('submods'),
    'DEPS', enable_recurse_deps=True, deps_path_prefix='infra',
    extra_submodules=['out=https://chromium.googlesource.com/infra/out']
  )


def GenTests(api):
  yield (
      api.test('basic')
  )
