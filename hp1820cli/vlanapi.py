#!/usr/bin/env python3
import sys

from hp1820cli.cli import Cli
from hp1820cli import shell


def getConfig(args):
    cli = _connectAndLogin(args['host'], args['user'], args['password'])
    membership_tuples = cli.getVlanMembership()
    _saveAndLogout(cli)
    return membership_tuples

def setPortToVlan(args, port, vlan_id):
    cli = _connectAndLogin(args['host'], args['user'], args['password'])
    cli.accessVlan('untagged', port, vlan_id)
    _saveAndLogout(cli)

def _connectAndLogin(host, user, password):
    if not Cli.testConnection('https', host):
        raise RuntimeError("Cannot connect to remote host")

    cli = Cli('https', host)

    if not cli.login(user, password):
        raise RuntimeError("Cannot login.")

    return cli

def _saveAndLogout(cli):
    cli.saveConfig()
    cli.logout()
    cli.close()
