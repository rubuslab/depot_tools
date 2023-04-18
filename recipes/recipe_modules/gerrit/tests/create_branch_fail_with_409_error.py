# Copyright 2023 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import post_process

DEPS = [
    'gerrit',
    'recipe_engine/json',
    'recipe_engine/raw_io',
    'recipe_engine/step',
]


def RunSteps(api):
  host = 'https://chromium-review.googlesource.com'
  project = 'v8/v8'

  branch = 'test'
  commit = '67ebf73496383c6777035e374d2d664009e2aa5c'

  data = api.gerrit.create_gerrit_branch(host, project, branch, commit)
  assert data == 'refs/heads/test'


def GenTests(api):
  yield api.test(
      'got_409_but_branch_created',
      api.step_data('gerrit create_gerrit_branch (v8/v8 test)', retcode=1),
      api.step_data(
          'confirm (v8/v8 test).gerrit Get branch ref',
          api.json.output({
              'revision': '67ebf73496383c6777035e374d2d664009e2aa5c',
              'ref': 'refs/heads/test'
          })),
      api.post_process(post_process.StepException,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'got_409_and_branch_created_at_unexpected_commit',
      api.step_data('gerrit create_gerrit_branch (v8/v8 test)', retcode=1),
      api.step_data(
          'confirm (v8/v8 test).gerrit Get branch ref',
          api.json.output({
              'revision': 'some_other_commit',
              'ref': 'refs/heads/test'
          })),
      api.post_process(post_process.StepException,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.StepException, 'confirm (v8/v8 test)'),
      api.post_process(post_process.StepTextContains, 'confirm (v8/v8 test)',
                       ['67ebf73496383c6777035e374d2d664009e2aa5c', 'Abort!']),
      api.post_process(post_process.StatusException),
      api.expect_exception('AssertionError'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'got_unexpected_error',
      api.step_data('gerrit create_gerrit_branch (v8/v8 test)', retcode=1),
      api.step_data('confirm (v8/v8 test).gerrit Get branch ref',
                    api.json.output({})),
      api.post_process(post_process.StepException,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.StepException, 'confirm (v8/v8 test)'),
      # Can not catch stdout from the test step, so only check
      # 'retcode: 1' in the step text.
      api.post_process(post_process.StepTextContains, 'confirm (v8/v8 test)',
                       ['retcode: 1']),
      api.post_process(post_process.StatusException),
      api.expect_exception('AssertionError'),
      api.post_process(post_process.DropExpectation),
  )
