#!/usr/bin/env python3
# Copyright 2024 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import json
import os
import subprocess
import sys
import textwrap

import utils

_DEFAULT_CONFIG_PATH = utils.depot_tools_config_path("build_telemetry.cfg")

_VERSION = 1

_DEFAULT_COUNTDOWN = 10


class Config:

    def __init__(self, config_path):
        self._config_path = config_path
        self._config = None
        self._notice_displayed = False

    def load(self):
        """Loads the build telemetry config."""
        if self._config:
            return

        config = None
        if os.path.isfile(self._config_path):
            with open(self._config_path, "r") as f:
                try:
                    config = json.load(f)
                except Exception:
                    pass
                if config.get("version") != _VERSION:
                    config = None  # Reset the state for version change.

        if not config:
            config = {
                "is_googler": is_googler(),
                "status": None,
                "countdown": _DEFAULT_COUNTDOWN,
                "version": _VERSION,
            }

        self._config = config

    def save(self):
        with open(self._config_path, "w") as f:
            json.dump(self._config, f)

    def is_googler(self):
        if not self._config:
            return
        return self._config.get("is_googler") == True

    def enabled(self):
        # Do not call yield when it should not collect telemetry.
        if not self._config:
            print("WARNING: depot_tools.build_telemetry: %s is not loaded." %
                  self._config_path,
                  file=sys.stderr)
            return
        if not self._config.get("is_googler"):
            return
        if self._config.get("status") == "opt-out":
            return
        self._show_notice()

        # Telemetry collection will happen.
        return True

    def _show_notice(self):
        """Dispalys notice when necessary."""
        if self._notice_displayed:
            return
        if self._config.get("countdown") == 0:
            return
        if self._config.get("status") == "opt-in":
            return
        print(
            textwrap.dedent("""\
            *** NOTICE ***
            Google-internal telemetry (including build logs, username, and hostname) is collected on corp machines to diagnose performance and fix build issues. This reminder will be shown $num more times. See http://go/chrome-build-telemetry for details. Hide this notice or opt out by running: build_telemetry [opt-in] [opt-out]
            *** END NOTICE ***
            """))
        self._notice_displayed = True
        self._config["countdown"] = max(0, self._config["countdown"] - 1)
        self.save()

    def opt_in(self):
        self._config["status"] = "opt-in"
        self.save()
        print("build telemetry collection is opted in")

    def opt_out(self):
        self._config["status"] = "opt-out"
        self.save()
        print("build telemetry collection is opted out")


def _load_config():
    """Loads the config from the default location."""
    cfg = Config(_DEFAULT_CONFIG_PATH)
    cfg.load()
    return cfg


def _is_googler():
    """Checks whether this user is Googler or not."""
    p = subprocess.run(
        "cipd auth-info",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=True,
    )
    if p.returncode != 0:
        return False
    lines = p.stdout.splitlines()
    if len(lines) == 0:
        return False
    l = lines[0]
    # |l| will be like 'Logged in as <user>@google.com.' for googler using
    # reclient.
    return l.startswith("Logged in as ") and l.endswith("@google.com.")


def enabled():
    """Checks whether the build can upload build telemetry."""
    cfg = _load_config()
    return cfg.enabled()


def main(argv):
    cfg = _load_config()

    if not cfg.is_googler():
        cfg.save()
        return

    if len(argv) == 2:
        if argv[1] == "opt-in":
            cfg.opt_in()
            return
        if argv[1] == "opt-out":
            cfg.opt_out()
            return

    print("Invalid arguments. Please run `build_telemetry [opt-in] [opt-out]`",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
