#!/usr/bin/env python
# -*- coding: utf-8 -*-

# SPDX-FileCopyrightText: 2021 Robin Schneider <ypid@riseup.net>
#
# SPDX-License-Identifier: MIT

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'community'
}

DOCUMENTATION = '''
---
module: my_sample_module

short_description: Assign VLANs to ports on HPE 1820 web managed switches.

#  version_added: "2.4"

description:
    - "This module provides declarative management of VLANs on HPE 1820 switches."
    - "Known limitation: The switch does not clear the session which means it runs out of sessions after 5 runs?."
    - "Known limitation: No option to remove VLANs from the table exists yet."

options:
    port_vlans:
        description:
            - Port to VLANs mapping dict. See example for the structure.
        required: true
    host:
        description:
            - Hostname of the switch.
        required: true
    username:
        description:
            - Username to login on the switch as.
        required: true
    password:
        description:
            - Password to use for login.
        required: true

author:
    - Robin Schneider (@ypid)
'''

EXAMPLES = '''
- name: Ensure port 2 has two VLANs assigned
  hpe1820_port_vlans:
    port_vlans:
      '2':
        untagged: 2900
        tagged:
          - 295
    host: '{{ inventory_hostname }}'
    username: '{{ hpe1820__username | d(omit) }}'
    password: '{{ hpe1820__password }}'
  delegate_to: 'localhost'

# The --diff output might look like this:
#
# --- before
# +++ after
# @@ -0,0 +1,3 @@
# +vlan_per_port('untagged', '2', 2900)
# +vlan_per_port('tagged', '2', 295)
# +vlan_per_port('exclude', '2', 2902)
'''

#  RETURN = '''
#  port_vlans:
#      description: All port VLANs of the switch after modifications.
#      type: dict
#  '''


from ansible.module_utils.basic import AnsibleModule
import lib.cli


def run_module():

    result = {
        'changed': False,
    }

    module = AnsibleModule(
        argument_spec=dict(
            port_vlans=dict(required=True, type='dict'),
            host=dict(required=True, type='str'),
            username=dict(required=False, type='str', default='admin'),
            password=dict(required=True, type='str', no_log=True),
        ),
        supports_check_mode=True,
    )

    port_vlans = module.params['port_vlans']
    host = module.params['host']
    username = module.params['username']
    password = module.params['password']

    # Always try https first!
    if lib.cli.Cli.testConnection('https', host):
        cli = lib.cli.Cli('https', host)
    else:
        if lib.cli.Cli.testConnection('http', host):
            cli = lib.cli.Cli('http', host)
        else:
            module.fail_json(msg="Error: Cannot connect to remote host through HTTP and HTTPS.", **result)

    cli.login(username, password)

    change_actions = cli.ensure_interfaces_vlan_membership(port_vlans, dry_run=module.check_mode)

    # This only slows it down. Could be made conditional if anybody has a valid use case for it.
    #  result['port_vlans'] = cli.get_interfaces_vlan_membership()

    if len(change_actions) > 0:
        result['changed'] = True
        result['diff'] = {
            'before': '',
            'after': '\n'.join([f"vlan_per_port{s}" for s in change_actions]) + '\n',
        }

    cli.logout()
    cli.close()

    module.exit_json(**result)


def main():
    run_module()


if __name__ == '__main__':
    main()
