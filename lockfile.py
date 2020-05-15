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

# Windows specific constants
WIN_GENERIC_WRITE = 0x40000000
WIN_LOCKFILE_EXCLUSIVE_LOCK = 0x00000002
WIN_LOCKFILE_FAIL_IMMEDIATELY = 0x00000001
WIN_BYTES_TO_LOCK = 1


class LockError(Exception):
  pass


class _BaseLockfile(object):
  """Abstract class to represent a cross-platform process-specific lockfile.

  Note: Lockfile is never removed from the filesystem.
  """

  def __init__(self, path, timeout=0):
    self.path = os.path.abspath(path)
    self.timeout = timeout
    self.lockfile = self.path + '.locked'
    self._is_locked = False

  def _lock(self):
    """_lock creates a file and acquires lock on it."""
    raise NotImplementedError('_lock must be implemented by child.')

  def _release(self):
    """_release removes lock and closes fd/handle."""
    raise NotImplementedError('_release must be implemented by child.')

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
        if elapsed < self.timeout:
          sleep_time = min(10, self.timeout - elapsed)
          logging.info(
              'Could not create git cache lockfile; '
              'will retry after sleep(%d).', sleep_time)
          elapsed += sleep_time
          time.sleep(sleep_time)
          continue
        raise LockError("Error locking %s (err: %s)" % (self.path, str(e)))

  def unlock(self):
    """Release the lock."""
    assert self._is_locked == True
    self._release()


class _UnixLockfile(_BaseLockfile):
  """_UnixLockfile is unix specific implementation of Lockfile."""

  def __init__(self, path, timeout=0):
    assert sys.platform.startswith('win') == False
    super(_UnixLockfile, self).__init__(path, timeout)
    self._fd = None

  def _lock(self):
    if self._is_locked:
      return
    assert self._fd is None

    open_flags = (os.O_CREAT | os.O_WRONLY)
    self._fd = os.open(self.lockfile, open_flags, 0o644)

    try:
      fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
      self._is_locked = True
    except Exception:
      self._release()
      raise

  def _release(self):
    if self._is_locked:
      fcntl.flock(self._fd, fcntl.LOCK_UN)
      self._is_locked = False

    if self._fd:
      os.close(self._fd)
      self._fd = None


class _WinLockfile(_BaseLockfile):
  """_WinLockfile is Windows specific implementation of Lockfile."""

  def __init__(self, path, timeout=0):
    assert sys.platform.startswith('win')
    super(_WinLockfile, self).__init__(path, timeout)
    self._handle = None

  def _lock(self):
    if self._is_locked:
      return
    assert self._handle is None

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

    self._handle = ctypes.wintypes.HANDLE(
        fn(
            self.lockfile,  # lpFileName
            WIN_GENERIC_WRITE,  # dwDesiredAccess
            0,  # dwShareMode=prevent others from opening file
            2,  # dwCreationDisposition=create file, always
            0  # pCreateExParams
        ))

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
        self._handle,  # hFile
        WIN_LOCKFILE_FAIL_IMMEDIATELY | WIN_LOCKFILE_EXCLUSIVE_LOCK,  # dwFlags
        0,  #dwReserved
        WIN_BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
        0,  # nNumberOfBytesToLockHigh
        Overlapped()  # lpOverlapped
    )
    # LockFileEx returns result as bool, which is converted into an integer
    # (1 == successful; 0 == not successful)
    if ret == 0:
      self._release()
      error_code = ctypes.GetLastError()
      raise OSError('Failed to lock handle (error code: %d).' % error_code)

    self._is_locked = True

  def _release(self):
    # Release the lock
    if self._is_locked:
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
          self._handle,  # hFile
          0,  #dwReserved
          WIN_BYTES_TO_LOCK,  # nNumberOfBytesToLockLow
          0,  # nNumberOfBytesToLockHigh
          Overlapped()  # lpOverlapped
      )
      self._is_locked = False

    # Close handle
    if self._handle:
      # https://docs.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-closehandle
      fn = ctypes.windll.kernel32.CloseHandle
      fn.argtypes = [
          ctypes.wintypes.HANDLE,  # hFile
      ]
      fn(self._handle)
      self._handle = None


if sys.platform.startswith('win'):
  Lockfile = _WinLockfile
else:
  Lockfile = _UnixLockfile


@contextlib.contextmanager
def lock(path, timeout=0):
  """Prefered way of using lockfile library.

  Usage:
    import lockfile
    with lockfile.Lock(path, timeout):
      # Do something
      pass

   """
  l = Lockfile(path, timeout)
  l.lock()
  try:
    yield
  finally:
    l.unlock()
