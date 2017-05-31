# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'git',
  'recipe_engine/context',
  'recipe_engine/path',
  'recipe_engine/raw_io',
  'recipe_engine/shutil',
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
    submodules = ['foo', 'bar']
    submodule_commits = {}

    # Set up our submodule repository as a commit on top of CHECKOUT_REPOSITORY
    # HEAD.
    base_repo = tdir.join('checkout')
    api.shutil.makedirs('repo', base_repo)
    with api.context(cwd=base_repo):
      api.git('init')
      for submodule in submodules:
        api.git('submodule', 'add', CHECKOUT_REPOSITORY, submodule)
      api.git('commit', '-a', '--no-verify', '-m', 'Submodules')
    setup_commit = api.git.rev_parse(base_repo)
    for submodule in submodules:
      path = base_repo.join(submodule)
      submodule_commits[submodule] = api.git.rev_parse(path)

    # Clone the created repository.
    repo = api.git.repository(
        api.git.url_for_path(base_repo),
        tdir.join('working'),
        use_git_cache=True)
    api.git.ensure_checkout(repo, recursive=True, clean=True)
    checkout_commit = api.git.rev_parse(repo.path)
    assert setup_commit == checkout_commit

    # Ensure that the submodules were also cloned.
    for submodule in submodules:
      submodule_commit = api.git.rev_parse(base_repo.join(submodule))
      assert submodule_commit == submodule_commits[submodule]


def GenTests(api):
  yield api.test('basic')
