# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_api


class Deps2SubmodulesApi(recipe_api.RecipeApi):
  def __call__(self, deps_repo, submodules_repo, deps_path='DEPS',
               enable_recurse_deps=False,
               deps_path_prefix=None, extra_submodules=()):
    """
    Args:
      deps_repo: fully-qualified path to the repo containing the DEPS file
      submodules_repo: fully-qualified path to the repo with the gitmodules
      deps_path: path to DEPS within deps_repo
          (default: DEPS)
      enable_recurse_deps: output submodules for dependencies in recursed DEPS
      deps_path_prefix: only include deps whose paths start with this
      extra_submodules: a list of "path=URL" strings added as extra submodules
    """
    cmd = [
        'python',
        self.resource('deps2submodules.py'),
        self.m.path.join(deps_repo, deps_path),
    ]
    if enable_recurse_deps:
      cmd.append('--enable-recurse-deps')
    if deps_path_prefix:
      cmd.extend(['--path-prefix', deps_path_prefix])
    for extra_submodule in extra_submodules:
      cmd.extend(['--extra-submodule', extra_submodule])

    with self.m.context(cwd=submodules_repo):
      self.m.step('deps2submodules', cmd)
