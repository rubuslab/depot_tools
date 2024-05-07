# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process
from recipe_engine.recipe_api import Property

from RECIPE_MODULES.depot_tools.bot_update import RelativeRoot

PYTHON_VERSION_COMPATIBILITY = 'PY3'

DEPS = [
    'bot_update',
    'gclient',
    'recipe_engine/assertions',
    'recipe_engine/buildbucket',
    'recipe_engine/path',
    'recipe_engine/properties',
]

PROPERTIES = {
    'expected_checkout_dir': Property(),
    'expected_repo_root_name': Property(),
    'expected_patch_root_name': Property(default=None),
}


def RunSteps(api, expected_checkout_dir, expected_repo_root_name,
             expected_patch_root_name):
  api.gclient.set_config('depot_tools')
  result = api.bot_update.ensure_checkout(return_custom_result=True)

  api.assertions.assertEqual(result.checkout_dir, expected_checkout_dir)

  api.assertions.assertEqual(result.repo_root.name, expected_repo_root_name)
  api.assertions.assertEqual(result.repo_root.path,
                             expected_checkout_dir / expected_repo_root_name)

  if expected_patch_root_name is not None:
    api.assertions.assertEqual(result.patch_root.name, expected_patch_root_name)
    api.assertions.assertEqual(result.patch_root.path,
                               expected_checkout_dir / expected_patch_root_name)
  else:
    api.assertions.assertIsNone(result.patch_root)

  api.assertions.assertEqual(result.properties,
                             result.json.output.get('properties', {}))
  api.assertions.assertEqual(result.manifest,
                             result.json.output.get('manifest', {}))
  api.assertions.assertEqual(result.fixed_revisions,
                             result.json.output.get('fixed_revisions', {}))


def GenTests(api):
  yield api.test(
      'basic',
      api.properties(
          expected_checkout_dir=api.path.start_dir,
          expected_repo_root_name='depot_tools',
      ),
      api.expect_status('SUCCESS'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'patch',
      api.buildbucket.try_build(),
      api.properties(
          expected_checkout_dir=api.path.start_dir,
          expected_repo_root_name='depot_tools',
          expected_patch_root_name='depot_tools',
      ),
      api.expect_status('SUCCESS'),
      api.post_process(post_process.DropExpectation),
  )
