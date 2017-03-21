#!/usr/bin/env python3
import sys

from lib.cli import Cli
from lib import hpshell

def checkArgument():
    if (len(sys.argv) == 4 and sys.argv[3] == 'show') or (len(sys.argv) == 5):
        return
    print("Usage for config vlan: sshhp user@host password interface accessVlanID")
    print("Usage for show vlan membership: sshhp user@host password show")
    raise SystemExit

def parseArgument():
    args = {}
    args['user'], args['host'] = sys.argv[1].split('@')
    args['password'] = sys.argv[2]
    if sys.argv[3] == 'show':
        args['show'] = True
    else:
        args['show'] = False
        args['interface'] = sys.argv[3]
        args['vlanId'] = sys.argv[4]
    return args

if __name__ == "__main__":
    checkArgument()
    args = parseArgument()

    # Support HTTPS only
    if not Cli.testConnection('https', args['host']):
        print("Cannot connect to remote host")
        raise SystemExit

    cli = Cli('https', args['host'])
    print("Connect through HTTPS successfully")
    print("Note: This program will NOT verify the SSL certificate.")

    if not cli.login(args['user'], args['password']):
        print("Cannot login.")
        raise SystemExit

    if args['show']:
        cli.showVlanMembership()
    else:
        cli.accessVlan('untagged', args['interface'], args['vlanId'])

    cli.saveConfig()
    cli.logout()
    cli.close()
    raise SystemExit
