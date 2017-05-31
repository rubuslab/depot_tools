# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'git',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/raw_io',
  'recipe_engine/step',
  'recipe_engine/tempfile',
]


# This is the repository to use for checkout. This should be a
# publicly-accessible repository with reliable uptime so we can actually use
# "run" to test real checkout against it.
CHECKOUT_REPOSITORY = (
    'https://chromium.googlesource.com/chromium/tools/depot_tools.git')


def RunSteps(api):
  with api.tempfile.temp_dir('checkout') as tdir:
    repo = api.git.repository(
        CHECKOUT_REPOSITORY,
        tdir.join('checkout'),
        use_git_cache=True)
    commit = api.git.ensure_checkout(repo, clean=True)
    rev_parse_commit = api.git.rev_parse(repo.path)
    assert commit and rev_parse_commit == commit


def GenTests(api):
  yield api.test('basic')
