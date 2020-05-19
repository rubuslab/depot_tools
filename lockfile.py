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

  WIN_GENERIC_WRITE = 0x40000000
  WIN_LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
  WIN_LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
  WIN_BYTES_TO_LOCK = 1
else:
  import fcntl


class LockError(Exception):
  pass


if sys.platform.startswith('win'):
  # Windows implementation
  def _try_lock(lockfile):
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

    handle = ctypes.wintypes.HANDLE(
        fn(
            lockfile,  # lpFileName
            WIN_GENERIC_WRITE,  # dwDesiredAccess
            0,  # dwShareMode=prevent others from opening file
            2,  # dwCreationDisposition=create file, always
            0  # pCreateExParams
        ))

    def close_handle():
      # https://docs.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
      fn = ctypes.windll.kernel32.CloseHandle
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
      ]
      fn(handle)

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
        handle,  # hFile
        WIN_LOCKFILE_FAIL_IMMEDIATELY | WIN_LOCKFILE_EXCLUSIVE_LOCK,  # dwFlags
        0,  #dwReserved
        WIN_BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
        0,  # nNumberOfBytesToLockHigh
        Overlapped()  # lpOverlapped
    )
    # LockFileEx returns result as bool, which is converted into an integer
    # (1 == successful; 0 == not successful)
    if ret == 0:
      error_code = ctypes.GetLastError()
      close_handle()
      raise OSError('Failed to lock handle (error code: %d).' % error_code)

    def release():
      # https://docs.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-unlockfileex
      fn = ctypes.windll.kernel32.UnlockFileEx
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
          ctypes.wintypes.DWORD,  # dwReserved
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockLow
          ctypes.wintypes.DWORD,  # nNumberOfBytesToLockHigh
          ctypes.POINTER(Overlapped),  # lpOverlapped
      ]
      try:
        fn(
            handle,  # hFile
            0,  #dwReserved
            WIN_BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
            0,  # nNumberOfBytesToLockHigh
            Overlapped()  # lpOverlapped
        )
      finally:
        close_handle()

    return release
else:
  # Unix implementation
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
    with lockfile.Lock(path, timeout):
      # Do something
      pass

   """
  release_fn = _lock(path, timeout)
  try:
    yield
  finally:
    release_fn()
