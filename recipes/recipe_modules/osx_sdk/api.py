# Copyright 2018 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""The `osx_sdk` module provides safe functions to access a semi-hermetic
XCode installation.

Available only to Google-run bots."""

from contextlib import contextmanager

from recipe_engine import recipe_api


class OSXSDKApi(recipe_api.RecipeApi):
  """API for using OS X SDK distributed via CIPD."""

  KNOWN_VERSIONS = frozenset((
    '8a218a',
    '8e3004b',
    '9a235',
    '9c40b',
  ))

  def __init__(self, sdk_properties, *args, **kwargs):
    super(OSXSDKApi, self).__init__(*args, **kwargs)

    self._sdk_version = sdk_properties['sdk_version']
    self._tool_pkg = sdk_properties['toolchain_pkg']
    self._tool_ver = sdk_properties['toolchain_ver']

  def initialize(self):
    assert self._sdk_version in self.KNOWN_VERSIONS, (
      'unknown SDK version %r' % (version,))

  @contextmanager
  def __call__(self, kind, enabled=True):
    """Setups the SDK environment when enabled.

    The helper tool will be deployed to [START_DIR]/cache/mac_toolchain.
    The SDK will be deployed to [START_DIR]/cache/osx_sdk.$version.app.

    To avoid machines rebuilding these on every run, set up named caches in your
    cr-buildbucket.cfg file like:

        caches: {
          # Cache for mac_toolchain tool
          name: "mac_toolchain_tool"
          path: "mac_toolchain"
        }
        caches: {
          # Cache for Xcode 9.2 (build version 9C40b)
          name: "xcode_ios_9C40b"
          path: "osx_sdk.9C40b.app"
        }

    Args:
      kind ('mac'|'ios'): How the SDK should be configured.
      enabled (bool): Whether the SDK should be used or not.

    Raises:
        StepFailure or InfraFailure.
    """
    assert kind in ('mac', 'ios'), 'Invalid kind %r' % (kind,)
    if not enabled:
      yield
      return

    try:
      with self.m.context(infra_steps=True):
        app = self._ensure_sdk(kind)
        self.m.step('select XCode', ['sudo', 'xcode-select', '--switch', app])
      yield
    finally:
      with self.m.context(infra_steps=True):
        self.m.step('reset XCode', ['sudo', 'xcode-select', '--reset'])

  def _ensure_sdk(self, kind):
    """Ensures the mac_toolchain tool and OS X SDK packages are installed.

    Returns Path to the installed sdk app bundle."""
    mac_toolchain_dir = self.m.path['cache'].join('mac_toolchain')

    ef = self.m.cipd.EnsureFile()
    ef.add_package(self._tool_pkg, self._tool_ver)
    self.m.cipd.ensure(mac_toolchain_dir, ef)

    sdk_app = self.m.path['cache'].join('osx_sdk.%s.app' % (self._sdk_version,))
    self.m.step('install xcode', [
        mac_toolchain_dir.join('mac_toolchain'), 'install',
        '-kind', kind,
        '-xcode-version', self._sdk_version,
        '-output-dir', sdk_app,
    ])
    return sdk_app
