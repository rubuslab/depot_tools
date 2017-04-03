# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import DEPS
CONFIG_CTX = DEPS['path'].CONFIG_CTX


@CONFIG_CTX()
def path_base(c):
  # Layout base directories for our various configurations.
  #
  # This may be used by a given configuration, if it is valid, and can also be
  # used by "all_builder_cache_dirs" when calculating cache directories for all
  # supported configs.

  # Determine "/b" by walking up from "start_dir".
  b_dir = c.START_DIR
  while b_dir and b_dir[-1] != 'b':
    b_dir = b_dir[:-1]
  if b_dir:
    c.base_paths['infra_b_dir'] = b_dir


  # infra_kitchen: Determine cache: <cache_root>/c
  if c.PLATFORM in ('linux', 'mac'):
    kitchen_cache_root = ('/', 'b')
  elif b_dir:
    kitchen_cache_root = b_dir
  else:  # pragma: no cover
    kitchen_cache_root = c.START_DIR
  c.base_paths['infra_kitchen_cache'] = kitchen_cache_root + ('c',)


@CONFIG_CTX(includes=['path_base'])
def infra_common(c):
  c.dynamic_paths['checkout'] = None


@CONFIG_CTX(includes=['infra_common'])
def infra_buildbot(c):
  c.base_paths['root'] = c.base_paths['infra_b_dir'] = c.START_DIR[:-4]
  c.base_paths['cache'] = c.base_paths['root'] + (
      'build', 'slave', 'cache')
  c.base_paths['git_cache'] = c.base_paths['root'] + (
      'build', 'slave', 'cache_dir')
  c.base_paths['goma_cache'] = c.base_paths['root'] + (
      'build', 'slave', 'goma_cache')
  for token in ('build_internal', 'build', 'depot_tools'):
    c.base_paths[token] = c.base_paths['root'] + (token,)


@CONFIG_CTX(includes=['infra_common'])
def infra_kitchen(c):
  c.base_paths['root'] = c.START_DIR
  # TODO(phajdan.jr): have one cache dir, let clients append suffixes.

  c.base_paths['cache'] = c.base_paths['infra_kitchen_cache']
  c.base_paths['builder_cache'] = c.base_paths['cache'] + ('b',)

  # Define our cache sub-paths.
  if c.PLATFORM in ('linux', 'mac') or 'infra_b_dir' in c.base_paths:
    cache_subpaths = ('git_cache', 'goma_cache', 'goma_deps_cache')
  else:  # pragma: no cover
    # For non-b-rooted Windows platforms, explicitly specify 'git_cache'.
    c.base_paths['git_cache'] = c.base_paths['root'] + ('cache_dir',)
    cache_subpaths = ('goma_cache', 'goma_deps_cache')
  for path in cache_subpaths:
    c.base_paths[path] = c.base_paths['cache'] + (path,)


@CONFIG_CTX(includes=['path_base'])
def infra_generic(c):
  c.base_paths['builder_cache'] = c.base_paths['cache'] + ('builder',)
  c.base_paths['git_cache'] = c.base_paths['cache'] + ('git',)
  c.base_paths['goma_cache'] = c.base_paths['cache'] + ('goma',)
