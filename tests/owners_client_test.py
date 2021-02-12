# Copyright (c) 2020 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import sys
import unittest

if sys.version_info.major == 2:
  import mock
else:
  from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gerrit_util
import owners_client

from testing_support import filesystem_mock


alice = 'alice@example.com'
bob = 'bob@example.com'
chris = 'chris@example.com'
dave = 'dave@example.com'
emily = 'emily@example.com'


def _get_owners():
  return {
    "code_owners": [
      {
        "account": {
          "email": 'approver@example.com'
        }
      },
      {
        "account": {
          "email": 'reviewer@example.com'
        },
      },
      {
        "account": {
          "email": 'missing@example.com'
        },
      }
    ]
  }


class DepotToolsClientTest(unittest.TestCase):
  def setUp(self):
    self.repo = filesystem_mock.MockFileSystem(
        files={
            '/OWNERS':
            '\n'.join([
                'per-file approved.cc=approver@example.com',
                'per-file reviewed.h=reviewer@example.com',
                'missing@example.com',
            ]),
            '/GLOBAL_APPROVERS':
            '\n'.join([
                'global@example.com',
            ]),
            '/approved.cc':
            '',
            '/reviewed.h':
            '',
            '/bar/insufficient_reviewers.py':
            '',
            '/bar/everyone/OWNERS':
            '*',
            '/bar/everyone/foo.txt':
            '',
            '/deeply/nested/file.txt':
            '',
        })
    self.root = '/'
    self.fopen = self.repo.open_for_reading
    mock.patch(
        'owners_client.DepotToolsClient._GetOriginalOwnersFiles',
        return_value={}).start()
    self.addCleanup(mock.patch.stopall)
    self.client = owners_client.DepotToolsClient(
        '/', 'branch', self.fopen, self.repo)

  def testListOwnersEveryone(self):
    self.assertEqual(['*', 'missing@example.com'],
                     self.client.ListOwners('bar/everyone/foo.txt', []))

  def testListOwners(self):
    self.assertEqual(['reviewer@example.com', 'missing@example.com'],
                     self.client.ListOwners('reviewed.h', []))

  def testListOwnersWithGlobalApproval(self):
    # global approvers and top level owners will appear in random order.
    self.assertEqual(
        set([
            'global@example.com', 'reviewer@example.com', 'missing@example.com'
        ]), set(self.client.ListOwners('reviewed.h', ['reviewed.h'])))
    self.assertEqual(
        set(['global@example.com', 'missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', ['deeply'])))
    # TODO: Should this include global approvals?
    self.assertEqual(
        set(['global@example.com', 'missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', ['/'])))
    # TODO: Should this include global approvals?
    self.assertEqual(
        set(['global@example.com', 'missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', ['*'])))
    # TODO: Is this equivalent to "GA="?
    self.assertEqual(
        set(['global@example.com', 'missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', [''])))
    # TODO: This fails, the global approvals shouldn't apply.
    self.assertEqual(
        set(['missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', ['deeply/n'])))
    # TODO: This fails, the global approvals shouldn't apply.
    self.assertEqual(
        set(['missing@example.com']),
        set(self.client.ListOwners('deeply/nested/file.txt', ['otherpath'])))


class GerritClientTest(unittest.TestCase):
  def setUp(self):
    self.client = owners_client.GerritClient('host', 'project', 'branch')

  @mock.patch('gerrit_util.GetOwnersForFile', return_value=_get_owners())
  def testListOwners(self, _get_owners_mock):
    self.assertEquals(
        ['approver@example.com', 'reviewer@example.com', 'missing@example.com'],
        self.client.ListOwners('bar/everyone/foo.txt', []))


class TestClient(owners_client.OwnersClient):
  def __init__(self, owners_by_path, global_approvers):
    super(TestClient, self).__init__()
    self.owners_by_path = owners_by_path
    self.global_approvers = global_approvers

  def ListOwners(self, path, global_approval_paths):
    owners = self.owners_by_path[path]
    for ga_path in global_approval_paths:
      if path.startswith(ga_path):
        owners += global_approvers
        break
    return sorted(set(owners))


class OwnersClientTest(unittest.TestCase):
  def setUp(self):
    self.owners = {}
    self.global_approvers = ['global@example.com']
    self.client = TestClient(self.owners, self.global_approvers)

  def testGetFilesApprovalStatus(self):
    self.client.owners_by_path = {
        'approved': ['approver@example.com'],
        'pending': ['reviewer@example.com'],
        'insufficient': ['insufficient@example.com'],
        'global': [],
        'everyone': [owners_client.OwnersClient.EVERYONE],
    }
    self.assertEqual(
        self.client.GetFilesApprovalStatus(
            ['approved', 'pending', 'insufficient', 'global'], [],
            ['approver@example.com'], ['reviewer@example.com']),
        {
            'approved': owners_client.OwnersClient.APPROVED,
            'pending': owners_client.OwnersClient.PENDING,
            'insufficient': owners_client.OwnersClient.INSUFFICIENT_REVIEWERS,
            'global': owners_client.OwnersClient.INSUFFICIENT_REVIEWERS,
        })
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['everyone'], [],
                                           ['anyone@example.com'], []),
        {'everyone': owners_client.OwnersClient.APPROVED})
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['everyone'], [], [],
                                           ['anyone@example.com']),
        {'everyone': owners_client.OwnersClient.PENDING})
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['everyone'], [], [], []),
        {'everyone': owners_client.OwnersClient.INSUFFICIENT_REVIEWERS})
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['global'], ['global'],
                                           ['anyone@example.com'], []),
        {'everyone': owners_client.OwnersClient.INSUFFICIENT_REVIEWERS})
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['global'], [''],
                                           ['global@example.com'], []),
        {'everyone': owners_client.OwnersClient.INSUFFICIENT_REVIEWERS})
    self.assertEqual(
        self.client.GetFilesApprovalStatus(['global'], ['global'],
                                           ['global@example.com'], []),
        {'everyone': owners_client.OwnersClient.APPROVED})

  def test_owner_combinations(self):
    owners = [alice, bob, chris, dave, emily]
    self.assertEqual(
        list(owners_client._owner_combinations(owners, 2)),
        [(bob, alice),
         (chris, alice),
         (chris, bob),
         (dave, alice),
         (dave, bob),
         (dave, chris),
         (emily, alice),
         (emily, bob),
         (emily, chris),
         (emily, dave)])

  def testScoreOwners(self):
    self.client.owners_by_path = {
        'a': [alice, bob, chris]
    }
    self.assertEqual(
      self.client.ScoreOwners(self.client.owners_by_path.keys()),
      [alice, bob, chris]
    )

    self.client.owners_by_path = {
        'a': [alice, bob],
        'b': [bob],
        'c': [bob, chris]
    }
    self.assertEqual(
      self.client.ScoreOwners(self.client.owners_by_path.keys()),
      [bob, alice, chris]
    )

    self.client.owners_by_path = {
        'a': [alice, bob],
        'b': [bob],
        'c': [bob, chris]
    }
    self.assertEqual(
      self.client.ScoreOwners(
          self.client.owners_by_path.keys(), exclude=[chris]),
      [bob, alice],
    )

    self.client.owners_by_path = {
        'a': [alice, bob, chris, dave],
        'b': [chris, bob, dave],
        'c': [chris, dave],
        'd': [alice, chris, dave]
    }
    self.assertEqual(
      self.client.ScoreOwners(self.client.owners_by_path.keys()),
      [chris, dave, alice, bob]
    )

  def testSuggestOwners(self):
    self.client.owners_by_path = {'a': [alice]}
    self.assertEqual(
        self.client.SuggestOwners(['a']),
        [alice])

    self.client.owners_by_path = {'abcd': [alice, bob, chris, dave]}
    self.assertEqual(
        sorted(self.client.SuggestOwners(['abcd'])),
        [alice, bob])

    self.client.owners_by_path = {'abcd': [alice, bob, chris, dave]}
    self.assertEqual(
        sorted(self.client.SuggestOwners(['abcd'], exclude=[alice, bob])),
        [chris, dave])

    self.client.owners_by_path = {
        'ae': [alice, emily],
        'be': [bob, emily],
        'ce': [chris, emily],
        'de': [dave, emily],
    }
    suggested = self.client.SuggestOwners(['ae', 'be', 'ce', 'de'])
    # emily should be selected along with anyone else.
    self.assertIn(emily, suggested)
    self.assertEqual(2, len(suggested))

    self.client.owners_by_path = {
        'ad': [alice, dave],
        'cad': [chris, alice, dave],
        'ead': [emily, alice, dave],
        'bd': [bob, dave],
    }
    self.assertEqual(
        sorted(self.client.SuggestOwners(['ad', 'cad', 'ead', 'bd'])),
        [alice, dave])

    self.client.owners_by_path = {
        'a': [alice],
        'b': [bob],
        'c': [chris],
        'ad': [alice, dave],
    }
    self.assertEqual(
        sorted(self.client.SuggestOwners(['a', 'b', 'c', 'ad'])),
        [alice, bob, chris])

    self.client.owners_by_path = {
        'abc': [alice, bob, chris],
        'acb': [alice, chris, bob],
        'bac': [bob, alice, chris],
        'bca': [bob, chris, alice],
        'cab': [chris, alice, bob],
        'cba': [chris, bob, alice]
    }
    suggested = self.client.SuggestOwners(
        ['abc', 'acb', 'bac', 'bca', 'cab', 'cba'])
    # Any two owners.
    self.assertEqual(2, len(suggested))

  def testBatchListOwners(self):
    self.client.owners_by_path = {
        'bar/everyone/foo.txt': [alice, bob],
        'bar/everyone/bar.txt': [bob],
        'bar/foo/': [bob, chris]
    }

    self.assertEquals(
        {
            'bar/everyone/foo.txt': [alice, bob],
            'bar/everyone/bar.txt': [bob],
            'bar/foo/': [bob, chris]
        },
        self.client.BatchListOwners(
            ['bar/everyone/foo.txt', 'bar/everyone/bar.txt', 'bar/foo/'], []))


class GetCodeOwnersClientTest(unittest.TestCase):
  def setUp(self):
    mock.patch('gerrit_util.IsCodeOwnersEnabled').start()
    self.addCleanup(mock.patch.stopall)

  def testGetCodeOwnersClient_GerritClient(self):
    gerrit_util.IsCodeOwnersEnabled.return_value = True
    self.assertIsInstance(
        owners_client.GetCodeOwnersClient('root', 'host', 'project', 'branch'),
        owners_client.GerritClient)

  def testGetCodeOwnersClient_DepotToolsClient(self):
    gerrit_util.IsCodeOwnersEnabled.return_value = False
    self.assertIsInstance(
        owners_client.GetCodeOwnersClient('root', 'host', 'project', 'branch'),
        owners_client.DepotToolsClient)


if __name__ == '__main__':
  unittest.main()
