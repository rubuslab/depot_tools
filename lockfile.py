# Copyright 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Exclusive filelocking for all supported platforms."""

from __future__ import print_function

import contextlib
import logging
import os
import sys
import time


class LockError(Exception):
  pass


if sys.platform.startswith('win'):
  # Windows implementation
  import win32imports

  BYTES_TO_LOCK = 1

  def _try_lock(lockfile):
    handle = win32imports.Handle(
        win32imports.CreateFileW(
            lockfile,  # lpFileName
            win32imports.GENERIC_WRITE,  # dwDesiredAccess
            0,  # dwShareMode=prevent others from opening file
            None,
            win32imports.
            CREATE_ALWAYS,  # dwCreationDisposition=create file, always
            win32imports.FILE_ATTRIBUTE_NORMAL,
            None  # hTemplateFile
        ))

    def close_handle():
      # https://docs.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
      win32imports.CloseHandle(handle)

    ret = win32imports.LockFileEx(
        handle,  # hFile
        win32imports.LOCKFILE_FAIL_IMMEDIATELY
        | win32imports.LOCKFILE_EXCLUSIVE_LOCK,  # dwFlags
        0,  #dwReserved
        BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
        0,  # nNumberOfBytesToLockHigh
        win32imports.Overlapped()  # lpOverlapped
    )
    # LockFileEx returns result as bool, which is converted into an integer
    # (1 == successful; 0 == not successful)
    if ret == 0:
      error_code = win32imports.GetLastError()
      close_handle()
      raise OSError('Failed to lock handle (error code: %d).' % error_code)

    def release():
      try:
        win32imports.UnlockFileEx(
            handle,  # hFile
            0,  #dwReserved
            BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
            0,  # nNumberOfBytesToLockHigh
            win32imports.Overlapped()  # lpOverlapped
        )
      finally:
        close_handle()

    return release
else:
  # Unix implementation
  import fcntl

  def _try_lock(lockfile):
    open_flags = (os.O_CREAT | os.O_WRONLY)
    fd = os.open(lockfile, open_flags, 0o644)

    try:
      fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except Exception:
      os.close(fd)
      raise

    def release():
      try:
        fcntl.flock(fd, fcntl.LOCK_UN)
      finally:
        os.close(fd)

    return release


def _lock(path, timeout=0):
  """_lock returns function to release the lock if locking was successful.

  _lock also implements simple retry logic."""
  elapsed = 0
  while True:
    try:
      return _try_lock(path + '.locked')
    except (OSError, IOError) as e:
      if elapsed < timeout:
        sleep_time = min(10, timeout - elapsed)
        logging.info(
            'Could not create git cache lockfile; '
            'will retry after sleep(%d).', sleep_time)
        elapsed += sleep_time
        time.sleep(sleep_time)
        continue
      raise LockError("Error locking %s (err: %s)" % (path, str(e)))


@contextlib.contextmanager
def lock(path, timeout=0):
  """Get exclusive lock to path.

  Usage:
    import lockfile
    with lockfile.lock(path, timeout):
      # Do something
      pass

   """
  release_fn = _lock(path, timeout)
  try:
    yield
  finally:
    release_fn()
