# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

PYTHON_VERSION_COMPATIBILITY = 'PY2+3'

DEPS = [
  'gsutil',
  'recipe_engine/platform',
  'recipe_engine/properties',
]


def RunSteps(api):
  with api.gsutil.disable_multiprocessing_on_mac():
    api.gsutil(['cp', 'gs://some/gs/path', '/some/local/path'])


def GenTests(api):
  yield api.test(
      'not_mac',
      api.platform('linux', 64),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mac_no_env',
      api.platform('mac', 64),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mac_with_boto_config',
      api.platform('mac', 64),
      api.properties.environ(
          BOTO_CONFIG='/some/boto/config'
      ),
      api.post_check(lambda check, steps: \
          check(steps['gsutil cp'].env['BOTO_CONFIG'] is None)),
      api.post_check(lambda check, steps: \
          check('/some/boto/config' in steps['gsutil cp'].env['BOTO_PATH'])),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'mac_with_boto_path',
      api.platform('mac', 64),
      api.properties.environ(
          BOTO_PATH='/some/boto/path'
      ),
      api.post_check(lambda check, steps: \
          check(steps['gsutil cp'].env['BOTO_CONFIG'] is None)),
      api.post_check(lambda check, steps: \
          check('/some/boto/path' in steps['gsutil cp'].env['BOTO_PATH'])),
      api.post_process(post_process.DropExpectation),
  )
