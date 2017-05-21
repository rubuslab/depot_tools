# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'gitiles',
    'recipe_engine/properties',
]


def RunSteps(api):
  url = 'https://chromium.googlesource.com/chromium/src'
  for ref in api.gitiles.refs(url):
    logs, _ = api.gitiles.log(url, ref)
    assert len(logs) == 3
  api.gitiles.commit_log(url, api.properties['commit_log_hash'])

  data = api.gitiles.download_file(url, 'OWNERS')
  assert data == 'foobar'


def GenTests(api):
  yield (
      api.test('basic')
      + api.properties(
          commit_log_hash=api.gitiles.make_hash('commit'),
      )
      + api.gitiles.refs('refs',
          'HEAD',
          'refs/heads/A',
          'refs/tags/B',
      )
      + api.gitiles.logs(
          'gitiles log: HEAD.fetch',
          'HEAD',
      )
      + api.gitiles.logs(
          'gitiles log: refs/heads/A.fetch',
          'HEAD',
      )
      + api.gitiles.logs(
          'gitiles log: refs/tags/B.fetch',
          'HEAD',
      )
      + api.gitiles.commit(
          'commit log: %s' % (api.gitiles.make_hash('commit')),
          'commit',
          'C',
          [
              'foo/bar',
              'baz/qux',
          ],
      )
      + api.gitiles.encoded_file(
          'fetch master:OWNERS',
          'foobar',
      )
  )
