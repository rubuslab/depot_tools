# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from recipe_engine import recipe_test_api


class TryserverTestApi(recipe_test_api.RecipeTestApi):
  def gerrit_change_info(self, **kwargs):
    return self.step_data(
        'gerrit fetch current CL info',
        self.m.gerrit.get_one_change_response_data(**kwargs)
    )
