#!/usr/bin/env python
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

if sys.platform.startswith('win'):
  import ctypes
  import ctypes.wintypes

  class Overlapped(ctypes.Structure):
    """Overlapped is required and used in LockFileEx and UnlockFileEx."""
    _fields_ = [('Internal', ctypes.wintypes.LPVOID),
                ('InternalHigh', ctypes.wintypes.LPVOID),
                ('Offset', ctypes.wintypes.DWORD),
                ('OffsetHigh', ctypes.wintypes.DWORD),
                ('Pointer', ctypes.wintypes.LPVOID),
                ('hEvent', ctypes.wintypes.HANDLE)]
else:
  import fcntl


class LockError(Exception):
  pass


class Lockfile(object):
  """Class to represent a cross-platform process-specific lockfile."""

  def __init__(self, path, timeout=0):
    self.path = os.path.abspath(path)
    self.timeout = timeout
    self.lockfile = self.path + ".lock"
    self._is_win = sys.platform.startswith('win')
    self._handler = None
    self._is_locked = False

  def _open_handler(self):
    # If file is already open, do nothing
    if self._handler:
      return

    if self._is_win:
      # https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
      fn = ctypes.windll.kernel32.CreateFile2
      fn.argtypes = [
          ctypes.wintypes.LPCWSTR,  # lpFileName
          ctypes.wintypes.DWORD,  # dwDesiredAccess
          ctypes.wintypes.DWORD,  # dwShareMode
          ctypes.wintypes.DWORD,  # dwCreationDisposition
          ctypes.wintypes.LPVOID,  # pCreateExParams
      ]
      fn.restype = ctypes.wintypes.HANDLE

      self._handler = ctypes.wintypes.HANDLE(
          fn(
              self.lockfile,  # lpFileName
              0x40000000,  # dwDesiredAccess=GENERIC_WRITE
              0,  # dwShareMode=prevent others from opening file
              2,  # dwCreationDisposition=create file, always
              0  # pCreateExParams
          ))
    else:
      open_flags = (os.O_CREAT | os.O_WRONLY)
      self._handler = os.open(self.lockfile, open_flags, 0o644)

  def _close_handler(self):
    if self._handler is None:
      return
    self._unlock()

    if self._is_win:
      # https://docs.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
      fn = ctypes.windll.kernel32.CloseHandle
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
      ]
      fn(self._handler)
    else:
      os.close(self._handler)
    self._handler = None

  def _lock(self):
    if self._is_locked:
      return

    self._open_handler()
    if self._is_win:
      # https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-lockfileex
      fn = ctypes.windll.kernel32.LockFileEx
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
          ctypes.wintypes.DWORD,  # dwFlags
          ctypes.wintypes.DWORD,  # dwReserved
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockLow
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockHigh
          ctypes.POINTER(Overlapped),  # lpOverlapped
      ]
      ret = fn(
          self._handler,  # hFile
          0x00000003,  # dwFlags=EXCLUSIVE_LOCK|FAIL_IMMEDIATELY
          0,  #dwReserved
          1,  # nNumberOfBytesToLockLow
          0,  # nNumberOfBytesToLockHigh
          Overlapped()  # lpOverlapped
      )
      # LockFileEx returns result as bool, which is converted into an integer
      # (1 == successful; 0 == not successful)
      if ret == 0:
        error_code = ctypes.windll.kernel32.GetLastError()
        raise OSError('Failed to lock handle (error code: %d).' % error_code)

    else:
      fcntl.flock(self._handler, fcntl.LOCK_EX | fcntl.LOCK_NB)
    self._is_locked = True

  def _unlock(self):
    if self._is_locked is False:
      return

    if self._is_win:
      # https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-unlockfileex
      fn = ctypes.windll.kernel32.UnlockFileEx
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
          ctypes.wintypes.DWORD,  # dwReserved
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockLow
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockHigh
          ctypes.POINTER(Overlapped),  # lpOverlapped
      ]
      fn(
          self._handler,  # hFile
          0,  #dwReserved
          1,  # nNumberOfBytesToLockLow
          0,  # nNumberOfBytesToLockHigh
          Overlapped()  # lpOverlapped
      )
    else:
      fcntl.flock(self._handler, fcntl.LOCK_UN)
    self._is_locked = False

  @contextlib.contextmanager
  def lock(self):
    """Acquire the lock.

    This will block with a deadline of self.timeout seconds.
    """
    assert self._is_locked == False
    elapsed = 0
    while True:
      try:
        self._lock()
        break
      except (OSError, IOError) as e:
        self._close_handler()
        if elapsed < self.timeout:
          sleep_time = min(10, self.timeout - elapsed)
          logging.info(
              'Could not create git cache lockfile; '
              'will retry after sleep(%d).', sleep_time)
          elapsed += sleep_time
          time.sleep(sleep_time)
          continue
        raise LockError("Error locking %s (err: %s)" % (self.path, str(e)))

    # Lock is successfully acquired.
    try:
      yield
    finally:
      self._unlock()
      self._close_handler()
      try:
        os.remove(self.lockfile)
      except OSError as e:
        logging.warning('Not able to delete lockfile %s (err: %s)' %
                        (self.lockfile, str(e)))
