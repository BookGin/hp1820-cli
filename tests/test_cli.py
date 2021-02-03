# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2021 Robin Schneider <ypid@riseup.net>
#
# SPDX-License-Identifier: MIT

from unittest import mock, TestCase
import textwrap

import yaml
import nose.tools

from lib.cli import Cli


class Test(TestCase):
    PORT_VLANS = yaml.safe_load(
        textwrap.dedent("""
        '1':
          untagged: 5
          tagged:
            - 142
            - 999
        '10':
          untagged: 5
          tagged:
            - 142
        """)
    )

    def setUp(self):
        self.c = Cli('https', 'localhost')

    def test__parse_port_range__exception(self):
        with self.assertRaises(Exception) as context:
            self.c._parse_port_range('TIRK5-TRK8')

        nose.tools.assert_in('port_range_part has unknown format: ', str(context.exception))

    def test__parse_port_range(self):
        nose.tools.assert_equal(
            self.c._parse_port_range('1, 9-11, 17-20, TRK2, TRK5-TRK8'),
            ['1', '9', '10', '11', '17', '18', '19', '20', 'TRK2', 'TRK5', 'TRK6', 'TRK7', 'TRK8']
        )

    def test_get_interfaces_vlan_membership(self):
        vlan_membership = yaml.safe_load(
            textwrap.dedent("""
            - []
            - - '5'
              - ''
              - '1,10'
              - ''
            - - '142'
              - '1,10'
              - ''
              - ''
            - - '999'
              - '1'
              - ''
              - ''
            """)
        )
        with mock.patch.object(Cli, 'getVlanMembership', return_value=vlan_membership):
            nose.tools.assert_equal(self.c.get_interfaces_vlan_membership(), self.PORT_VLANS)

    def test_ensure_interfaces_vlan_membership(self):
        desired_port_vlans = yaml.safe_load(
            textwrap.dedent("""
            '1':
              untagged: 90
              tagged:
                - 123
                - 142
            """)
        )
        expected_change_actions = [
            ('addVlan', 90),
            ('accessVlan', 'untagged', '1', 90),
            ('addVlan', 123),
            ('accessVlan', 'tagged', '1', 123),
            ('accessVlan', 'exclude', '1', 999),
        ]
        with mock.patch.object(Cli, 'get_interfaces_vlan_membership', return_value=self.PORT_VLANS):
            with mock.patch.object(Cli, 'getVlans', return_value=[]):
                change_actions = self.c.ensure_interfaces_vlan_membership(desired_port_vlans, dry_run=True)
        nose.tools.assert_equal(change_actions, expected_change_actions)

    def test_ensure_interfaces_vlan_membership_wrong_port(self):
        desired_port_vlans = yaml.safe_load(
            textwrap.dedent("""
            '99':
              untagged: 90
              tagged:
                - 123
                - 142
            """)
        )
        with mock.patch.object(Cli, 'get_interfaces_vlan_membership', return_value=self.PORT_VLANS):
            with self.assertRaises(Exception) as context:
                self.c.ensure_interfaces_vlan_membership(desired_port_vlans)

            nose.tools.assert_equal(
                'The switch does not have the following ports: 99',
                str(context.exception)
            )
