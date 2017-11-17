#!/usr/bin/env python
# Copyright (c) 2017 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Unit Tests for auth.py"""

import __builtin__
import datetime
import json
import logging
import os
import unittest
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from third_party import httplib2
from third_party.pymox import mox

import auth


class TestGetLuciContextAccessToken(mox.MoxTestBase):
  def _mock_local_auth(self, account_id, secret, rpc_port):
    default_test_path = 'default/test/path'
    self.mox.StubOutWithMock(os, 'environ')
    os.environ.get('LUCI_CONTEXT').AndReturn(default_test_path)
    local_auth_dict = {
      'default_account_id': account_id,
      'secret': secret,
      'rpc_port': rpc_port,
    }
    mock_file = self.mox.CreateMockAnything()
    self.mox.StubOutWithMock(__builtin__, 'open')
    mock_file.__enter__().AndReturn(mock_file)
    mock_file.read().AndReturn(json.dumps({'local_auth': local_auth_dict}))
    __builtin__.open(default_test_path).AndReturn(mock_file)
    mock_file.__exit__(mox.IgnoreArg(), mox.IgnoreArg(), mox.IgnoreArg())

  def _mock_loc_server_resp(self, status, content):
    mock_response = self.mox.CreateMockAnything()
    mock_response.status = status
    mock_http = self.mox.CreateMock(httplib2.Http)
    mock_http.request(
        uri=mox.IgnoreArg(),
        method=mox.IgnoreArg(),
        body=mox.IgnoreArg(),
        headers=mox.IgnoreArg()).AndReturn((mock_response, content))
    self.mox.StubOutWithMock(httplib2, 'Http', use_mock_anything=True)
    httplib2.Http().AndReturn(mock_http)

  # at times necessary because of __builtin__.open mock above
  def _mock_logging_ex(self):
    self.mox.StubOutWithMock(logging, 'exception')
    logging.exception(mox.IgnoreArg()).AndReturn(None)

  def testCorrectLocalAuthFormat(self):
    self._mock_local_auth('dead', 'beef', 10)
    expiry_time = datetime.datetime.utcnow() + datetime.timedelta(minutes=60)
    resp_content = {
      'error_code': None,
      'error_message': None,
      'access_token': 'token',
      'expiry': time.mktime(expiry_time.timetuple()),
    }
    self._mock_loc_server_resp(200, json.dumps(resp_content))
    self.mox.ReplayAll()
    token = auth.get_luci_context_access_token()
    self.assertEquals(token.token, 'token')

  def testIncorrectPortFormat(self):
    self._mock_local_auth('foo', 'bar', 'bar')
    self._mock_logging_ex()
    self.mox.ReplayAll()
    self.assertRaises(auth.LuciContextAuthError,
        auth.get_luci_context_access_token)

  def testNoAccountId(self):
    self._mock_local_auth(None, 'bar', 10)
    self.mox.ReplayAll()
    token = auth.get_luci_context_access_token()
    self.assertIsNone(token)

  def testExpiredToken(self):
    self._mock_local_auth('dead', 'beef', 10)
    resp_content = {
      'error_code': None,
      'error_message': None,
      'access_token': 'token',
      'expiry': time.mktime(datetime.datetime.min.timetuple()),
    }
    self._mock_loc_server_resp(200, json.dumps(resp_content))
    self.mox.ReplayAll()
    self.assertRaises(auth.LuciContextAuthError,
        auth.get_luci_context_access_token)

  def testIncorrectExpiryFormatReturned(self):
    self._mock_local_auth('dead', 'beef', 10)
    self._mock_logging_ex()
    resp_content = {
      'error_code': None,
      'error_message': None,
      'access_token': 'token',
      'expiry': 'dead',
    }
    self._mock_loc_server_resp(200, json.dumps(resp_content))
    self.mox.ReplayAll()
    self.assertRaises(auth.LuciContextAuthError,
        auth.get_luci_context_access_token)

  def testIncorrectResponseContentFormat(self):
    self._mock_local_auth('dead', 'beef', 10)
    self._mock_logging_ex()
    self._mock_loc_server_resp(200, '5')
    self.mox.ReplayAll()
    self.assertRaises(auth.LuciContextAuthError,
        auth.get_luci_context_access_token)


if __name__ == '__main__':
  if '-v' in sys.argv:
    logging.basicConfig(level=logging.DEBUG)
  unittest.main()
