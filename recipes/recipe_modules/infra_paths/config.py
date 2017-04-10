# Copyright 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import types

from recipe_engine.config import config_item_context, ConfigGroup, BadConf
from recipe_engine.config import Single
from recipe_engine.config_types import Path

def BaseConfig(**_kwargs):
  return ConfigGroup(
    volatile_tempdir=Single(bool)
  )

config_ctx = config_item_context(BaseConfig)

@config_ctx()
def infra_buildbot(c):
  c.volatile_tempdir = False


@config_ctx()
def infra_kitchen(c):
  c.volatile_tempdir = False


@config_ctx()
def infra_generic(c):
  c.volatile_tempdir = True


