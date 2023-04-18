# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'gerrit',
    'recipe_engine/json',
    'recipe_engine/step',
]


def RunSteps(api):
  host = 'https://chromium-review.googlesource.com'
  project = 'v8/v8'

  branch = 'test'
  commit = '67ebf73496383c6777035e374d2d664009e2aa5c'

  data = api.gerrit.create_gerrit_branch(host,
                                         project,
                                         branch,
                                         commit,
                                         allow_existent_branch=True)

  assert data == 'refs/heads/test'


def GenTests(api):

  yield api.test(
      'existent_branch_cut_at_expected_commit',
      api.step_data(
          'gerrit Get branch ref',
          api.json.output({
              'revision': '67ebf73496383c6777035e374d2d664009e2aa5c',
              'ref': 'refs/heads/test'
          })),
      api.post_process(post_process.DoesNotRun,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conflict_with_existent_branch',
      api.step_data(
          'gerrit Get branch ref',
          api.json.output({
              'revision': 'some_commit_hash',
              'ref': 'refs/heads/test'
          })),
      api.post_process(post_process.DoesNotRun,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.StatusException),
      api.post_process(post_process.DropExpectation),
      status='INFRA_FAILURE',
  )
