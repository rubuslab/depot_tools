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
  def common_step_data(commit, branch_existent=True):
    branch_info = {}
    if branch_existent:
      branch_info['revision'] = commit
      branch_info['ref'] = 'refs/heads/test'
    return sum([
        api.step_data('gerrit get_gerrit_branch (v8/v8 test)',
                      api.json.output({})),
        api.step_data('gerrit create_gerrit_branch (v8/v8 test)', retcode=1),
        api.step_data('confirm (v8/v8 test).gerrit Get branch ref',
                      api.json.output(branch_info)),
    ], api.empty_test_data())

  def common_post_check_on_failures(err_msg):
    return sum([
        api.post_process(post_process.StepException,
                         'gerrit create_gerrit_branch (v8/v8 test)'),
        api.post_process(post_process.StepException, 'confirm (v8/v8 test)'),
        api.post_process(post_process.StepTextContains, 'confirm (v8/v8 test)',
                         [err_msg]),
        api.post_process(post_process.StatusException),
        api.expect_exception('AssertionError'),
    ], api.empty_test_data())

  # Gerrit returns 409 if the branch was created. It could be done by
  # previous build or some earlier attempt. As long as the branch head
  # is at the commit we requested, we are good.
  yield api.test(
      'got_gerrit_409_but_branch_created',
      common_step_data('67ebf73496383c6777035e374d2d664009e2aa5c'),
      api.post_process(post_process.StepException,
                       'gerrit create_gerrit_branch (v8/v8 test)'),
      api.post_process(post_process.StatusSuccess),
      api.post_process(post_process.DropExpectation),
  )

  # Raise an exception if the branch head is pointing at a different commit.
  # Note, even if the branch is cut from the commit we asked, if there are
  # CLs submitted later, fail this call. Because we can not create a NEW branch
  # from this commit.
  yield api.test(
      'got_409_and_branch_created_at_unexpected_commit',
      common_step_data('some_commit_else'),
      common_post_check_on_failures(
          'v8/v8/test was not cut at '
          '67ebf73496383c6777035e374d2d664009e2aa5c. Abort!'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'got_unexpected_error',
      common_step_data('some_commit_else', branch_existent=False),
      # Can not catch stdout from the test step, so only check
      # 'retcode: 1' in the step text.
      common_post_check_on_failures('retcode: 1'),
      api.post_process(post_process.DropExpectation),
  )

  yield api.test(
      'conflict_with_existent_branch',
      api.step_data(
          'gerrit get_gerrit_branch (v8/v8 test)',
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
