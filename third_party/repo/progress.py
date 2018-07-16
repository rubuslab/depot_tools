#
# Copyright (C) 2009 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
from time import time

class Progress(object):
  def __init__(self, title, total=0):
    self._title = title
    self._total = total
    self._done = 0
    self._lastp = -1
    self._start = time()
    self._show = False
    self._width = 0

  def update(self, inc=1, extra=''):
    self._done += inc

    if not self._show:
      if 0.5 <= time() - self._start:
        self._show = True
      else:
        return

    text = None

    if self._total <= 0:
      text = '%s: %3d' % (self._title, self._done)
    else:
      p = (100 * self._done) / self._total

      if self._lastp != p:
        self._lastp = p
        text = '%s: %3d%% (%2d/%2d)' % (self._title, p,
                                        self._done, self._total)

    if text:
      text += ' ' + extra
      text = text[:self.terminal_width()]  # Avoid wrapping
      spaces = max(self._width - len(text), 0)
      sys.stdout.write('%s%*s\r' % (text, spaces, ''))
      sys.stdout.flush()
      self._width = len(text)

  def end(self):
    if not self._show:
      return

    if self._total <= 0:
      text = '%s: %d, done.' % (
        self._title,
        self._done)
    else:
      p = (100 * self._done) / self._total
      text = '%s: %3d%% (%d/%d), done.' % (
        self._title,
        p,
        self._done,
        self._total)

    spaces = max(self._width - len(text), 0)
    sys.stdout.write('%s%*s\n' % (text, spaces, ''))
    sys.stdout.flush()

  def terminal_width(self):
    """Returns sys.maxsize if the width cannot be determined."""
    try:
      if not sys.stdout.isatty():
        return sys.maxsize
      if sys.platform == 'win32':
        # From http://code.activestate.com/recipes/440694-determine-size-of-console-window-on-windows/
        from ctypes import windll, create_string_buffer
        handle = windll.kernel32.GetStdHandle(-12)  # -12 == stderr
        console_screen_buffer_info = create_string_buffer(22)  # 22 == sizeof(console_screen_buffer_info)
        if windll.kernel32.GetConsoleScreenBufferInfo(handle, console_screen_buffer_info):
          import struct
          _, _, _, _, _, left, _, right, _, _, _ = struct.unpack('hhhhHhhhhhh', console_screen_buffer_info.raw)
          # Note that we return 1 less than the width since writing into the rightmost column
          # automatically performs a line feed.
          return right - left
        return sys.maxsize
      else:
        import fcntl
        import struct
        import termios
        packed = fcntl.ioctl(sys.stderr.fileno(), termios.TIOCGWINSZ, '\0' * 8)
        _, columns, _, _ = struct.unpack('HHHH', packed)
        return columns
    except Exception:  # pylint: disable=broad-except
      return sys.maxsize
