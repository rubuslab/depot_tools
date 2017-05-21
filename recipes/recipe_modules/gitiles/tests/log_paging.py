# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'gitiles',
    'recipe_engine/properties',
    'recipe_engine/url',
]


def RunSteps(api):
  data, cursor = api.gitiles.log(
      'https://chromium.googlesource.com/chromium/src',
      'master',
      limit=7,
      cursor='foo')
  assert len(data) == 9
  assert cursor == 'qux'


def GenTests(api):
  yield (
      api.test('basic')
      + api.url.json(
          'gitiles log: master.foo... (cursor)',
          api.gitiles.make_log_dict('logs', cursor='bar'),
      )
      + api.url.json(
          'gitiles log: master.bar... (cursor)',
          api.gitiles.make_log_dict('logs', cursor='baz'),
      )
      + api.url.json(
          'gitiles log: master.baz... (cursor)',
          api.gitiles.make_log_dict('logs', cursor='qux'),
      )
  )
