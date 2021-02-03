# -*- coding: utf-8 -*-
#
# SPDX-FileCopyrightText: 2016 Bookgin <dongsheoil@gmail.com>
# SPDX-FileCopyrightText: 2021 Robin Schneider <ypid@riseup.net>
#
# SPDX-License-Identifier: MIT

import requests
import json
import time
import re as regex
from bs4 import BeautifulSoup
import urllib.request, urllib.error, ssl
from math import isnan
import re
import os
import functools


class Cli:
    def __init__(self, protocol, host):
        self.protocol, self.host = protocol, host
        self.session = requests.Session()

    @staticmethod
    def testConnection(protocol, host):
        url = protocol + PROTOCOL_DELIMETER + host
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        try:
            response = urllib.request.urlopen(url, timeout = TEST_CONNECTION_TIMEOUT, context = ctx)
        except urllib.error.URLError as err:
            print("Cannot connect %s : %s" % (url, err.reason))
            return False
        else:
            return True

    @staticmethod
    def _parse_port_range(port_range_str):
        port_range = []
        for port_range_part in port_range_str.replace(' ', '').split(','):
            _re = re.search(r"""
                ^
                (?P<port_prefix>[A-Z]*)
                (?P<first_if>[0-9]+)
                (?:
                    -
                    (?P=port_prefix)
                    (?P<last_if>[0-9]+)
                )?
                $
            """, port_range_part, flags=re.VERBOSE)
            if not _re:
                raise Exception(f"port_range_part has unknown format: {port_range_part}")
            matches = _re.groupdict()
            if matches['last_if'] is None:
                matches['last_if'] = matches['first_if']

            port_range_iter = range(
                int(matches['first_if']),
                int(matches['last_if']) + 1)
            for port_item in port_range_iter:
                port_range.append(f"{matches['port_prefix']}{port_item}")

        return port_range

    def login(self, username, password):
        try:
            raw_response = self._httpPost('login', {'username': username, 'password': password})
            response = json.loads(raw_response)
        except requests.exceptions.ConnectionError:
            response = {'error': 'Connection error'}

        if response['error']:
            print('Cannot login: ' + response['error'])
            return False
        else:
            return True

    def logout(self):
        self._httpGet('logout')
        print('Logout.')

    def close(self):
        self.session.close()
        print('Session closed.')


    # show function

    def showPortStatus(self):
        first_row = ['Interface', 'Admin Mode', 'Physical Type', 'Port Status', 'Physical Mode', 'Link Speed', 'MTU']
        showStatus(self._httpGet('port_status'), first_row)

    def showPortChannel(self):
        first_row = ['Interface', 'Name', 'Type', 'Admin Mode', 'Link Status', 'Members', 'Active Ports']
        showStatus(self._httpGet('port_channel'), first_row)

    def showVlanStatus(self):
        first_row = ['VLAN ID', 'Name', 'Type']
        showStatus(self._httpGet('vlan_status'), first_row)

    def showMacTable(self):
        first_row = ['VLAN ID', 'MAC Address', 'Interface', 'Interface Index', 'Status']
        showStatus(self._httpGet('mac_table'), first_row, ignore_first = False)

    def showPortStatistic(self):
        first_row = ['Int','RX w/o Err','RX with Err','RX Broadcast','TX w/o Err','TX with Err','Collision','TX PauseFrame','RX PauseFrame']
        showStatus(self._httpGet('port_statistic'), first_row, ignore_first = False)

    def showDashboard(self):
        printDashboard(self._httpGet('dashboard'))

    def _set_vlan_port_in_variable(self, port_vlans, vlan, index, mode):
        vid = int(vlan[0])
        if vlan[index] != '':
            for vlan_port in self._parse_port_range(vlan[index]):
                port_vlans.setdefault(vlan_port, {})
                if mode == 'untagged':
                    port_vlans[vlan_port][mode] = vid
                elif mode == 'tagged':
                    port_vlans[vlan_port].setdefault(mode, [])
                    port_vlans[vlan_port][mode].append(vid)

    def get_interfaces_vlan_membership(self):
        port_vlans = {}
        vlan_membership = self.getVlanMembership()
        for vlan in vlan_membership:
            if len(vlan) != 4:
                continue
            self._set_vlan_port_in_variable(port_vlans, vlan, 1, 'tagged')
            self._set_vlan_port_in_variable(port_vlans, vlan, 2, 'untagged')
            self._set_vlan_port_in_variable(port_vlans, vlan, 3, 'exclude')
        return port_vlans

    def get_interface_vlan_membership_change_actions(self, interface, port_vlans, desired_port_vlans):
        change_actions = []
        vlan_vids = [int(vlan[0]) for vlan in self.getVlans() if len(vlan) == 3]
        if 'untagged' in desired_port_vlans and port_vlans.get('untagged') != desired_port_vlans['untagged']:
            if desired_port_vlans['untagged'] not in vlan_vids:
                change_actions.append(('addVlan', desired_port_vlans['untagged']))
            change_actions.append(('accessVlan', 'untagged', interface, desired_port_vlans['untagged']))
        if 'tagged' in desired_port_vlans:
            for desired_tagged_vlan in desired_port_vlans['tagged']:
                if desired_tagged_vlan not in port_vlans.get('tagged', []):
                    if desired_tagged_vlan not in vlan_vids:
                        change_actions.append(('addVlan', desired_tagged_vlan))
                    change_actions.append(('accessVlan', 'tagged', interface, desired_tagged_vlan))
            for tagged_vlan in port_vlans.get('tagged', []):
                if tagged_vlan not in desired_port_vlans['tagged']:
                    change_actions.append(('accessVlan', 'exclude', interface, tagged_vlan))
        return change_actions

    def ensure_interfaces_vlan_membership(self, desired_port_vlans, dry_run=False):
        change_actions = []
        interfaces_vlan_membership = self.get_interfaces_vlan_membership()
        interfaces_not_existing_on_switch = []
        for interface in desired_port_vlans.keys():
            if interface not in interfaces_vlan_membership:
                interfaces_not_existing_on_switch.append(interface)
        if len(interfaces_not_existing_on_switch) > 0:
            raise Exception(f"The switch does not have the following ports: {','.join(interfaces_not_existing_on_switch)}")
        for interface, port_vlans in interfaces_vlan_membership.items():
            change_actions.extend(self.get_interface_vlan_membership_change_actions(
                interface,
                port_vlans,
                desired_port_vlans.get(interface, {}),
            ))
        if not dry_run:
            for change_action in change_actions:
                getattr(self, change_action[0])(*change_action[1:])
            if len(change_actions) > 0:
                self.saveConfig()

        return change_actions

    @functools.lru_cache()
    def _get_all_config(self):
        return self._httpGet('all_config')

    # TODO: Refactor out of Cli class.
    def getVlanMembership(self):
        html = BeautifulSoup(self._get_all_config(), 'html.parser')
        data = []
        for table in html.find_all("table"):
            if table["id"] != "sorttable12":
                continue
            for row in table.find_all("tr"):
                data.append([col.get_text() for col in row.find_all("td")])
        return data

    def getVlans(self):
        html = BeautifulSoup(self._get_all_config(), 'html.parser')
        data = []
        for table in html.find_all("table"):
            if table["id"] != "sorttable10":
                continue
            for row in table.find_all("tr"):
                data.append([col.get_text() for col in row.find_all("td")])
        return data

    def showVlanMembership(self):
        first_row = ['VLAN ID', 'Tagged Ports', 'Untagged Ports', 'Exclude Participation']
        printTable(first_row, self.getVlanMembership())

    # DEPRECATED: This method uses the same API as showDashboard()
    def getSwitchName(self):
        raw_response = self._httpGet('dashboard')
        html = BeautifulSoup(raw_response, 'html.parser')
        for row in html.find_all('tr'):
            cols = list(row.find_all('td'))
            if len(cols) == 2:
                (key, val) = (cols[0], cols[1])
                if key.get_text() == "System Name":
                    return val.input['value']


    # set function

    def setTimezoneTaipei(self):
        post_data = {
            'offset_sel[]': '77',
            'zone': 'TPE',
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        self._httpPost('set_timezone', post_data)

    def setSntp(self, sntp_ip):
        post_data = {
            'set_sys_time_sel[]': 'using_sntp',
            'client_mode_sel[]': 'enabled',
            'host_name_ipaddr': sntp_ip,
            'server_port': '123',
            'date_alt': '1970-1-1',
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        self._httpPost('set_sntp', post_data)

    def setSystemInfo(self, name, location, contact):
        post_data = {
            'sys_name': name,
            'sys_location': location,
            'sys_contact': contact,
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        self._httpPost('set_sysinfo', post_data)

    def setNetwork(self, mode, ip = '', subnet = '', gateway = '', mgmt_vlan = '1'):
        required_data = {
            'protocol_type_sel[]': mode,  # static or dhcp
            'session_timeout': '5',
            'mgmt_vlan_id_sel[]': mgmt_vlan,
            'mgmt_port_sel[]': 'none',
            'snmp_sel[]': 'enabled',
            'community_name': 'public',
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit',
            'change_mvlan': 'no',
            'change_mport': 'no'
        }
        post_data = {}
        post_data.update(required_data)

        if mode == "static":
            ip_data = {'ip_addr': ip, 'subnet_mask': subnet, 'gateway_address': gateway}
            post_data.update(ip_data)

        self._httpPost('set_network', post_data)

    def setAccount(self, username, old_pwd, new_pwd, confirm_new_passwd):
        post_data = {
            'user_name': username,
            'current_password': old_pwd,
            'new_password': new_pwd,
            'confirm_new_passwd': new_pwd,
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        response = self._httpPost('set_account', post_data)
        if 'Required field' in response:
            print("Cannot update password, required field is not valid")
        elif 'password is incorrect' in response:
            print("Cannot update password, current password is incorrect")
        else:
            print("Username/Password changed successfully")


    def accessVlan(self, mode, interfaces, vlan_id):
        post_data = {
            'part_tagg_sel[]': mode, # tagged, untagged, exclude
            'vlan': vlan_id,
            'intfStr': interfaces, # 1-8, TRK1: 54, TRK2: 55 ...
            'part_exclude': 'yes',
            'parentQStr': '?vlan=%s' % vlan_id, # looks like this doesn't matter
            'b_modal1_clicked': 'b_modal1_submit'
        }
        self._httpPost('access_vlan', post_data)
        self._get_all_config.cache_clear()

    # @param example: 5-18 or 7 or 1,4,7
    def addVlan(self, vlan_id_str):
        post_data = {
            'vlan_id_range': vlan_id_str,
            'vlancount': '1',
            'b_modal1_clicked': 'b_modal1_submit'
        }
        self._httpPost('add_vlan', post_data)
        self._get_all_config.cache_clear()

    # @param example: 5-18 or 7 or 1,4,7
    def delVlan(self, vlan_id_str):
        vlan_ids = parseIds(vlan_id_str)
        post_data = {
            'sorttable1_length': '-1',
            'chkrow[]': vlan_ids,
            'b_form1_clicked': 'b_form1_dt_remove'
        }
        self._httpPost('del_vlan', post_data)
        self._get_all_config.cache_clear()

    # Generate https SSL certificate.
    def genCert(self):
        post_data = {
            'http_mode_sel[]': 'enabled',
            'https_mode_sel[]': 'disabled',
            'soft_timeout': '5',
            'hard_timeout': '24',
            'certificate_stat': 'Absent',
            'b_form1_clicked': 'b_form1_bt_generate'
        }
        self._httpPost('https_config', post_data)
        while self._httpGet('cert_state') != 'Present':
            time.sleep(1)

    # set the management interface
    # @param "enabled", "disabled"
    def setHttps(self, http, https):
        post_data = {
            'http_mode_sel[]': http,
            'https_mode_sel[]': https,
            'soft_timeout': '5',
            'hard_timeout': '24',
            'certificate_stat': 'Present',
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        self._httpPost('https_config', post_data)

    def saveConfig(self):
        self._httpPost('save_config', {})

    def reset(self):
        self._httpPost('factory_default', {"b_form1_clicked": "b_form1_reset"})

    # Upload config file. The filename should be hp1820_8G.cfg. Other names are deprecated.
    def uploadConfig(self, filepath):
        post_data = {
            'file_type_sel[]': 'config',
            'orig_file_name': 'hp1820_8G.cfg',
            'optDSV': '1',
            'filename': 'hp1820_8G.cfg',
            'transfer_file': 'hp1820_8G.cfg'
        }
        files = {'transfer_file': open(filepath, 'rb')}
        self._httpPostFile('file_transfer', post_data, files)

    def uploadCode(self, filepath):
        filename = os.path.basename(filepath)
        post_data = {
            'file_type_sel[]': 'backup_code',
            'orig_file_name': filename,
            'optDSV': '1',
            'filename': filename,
            'transfer_file': filename
        }
        files = {'transfer_file': open(filepath, 'rb')}
        response = self._httpPostFile('file_transfer', post_data, files)
        print('Upload succeeded. Please activate the code now.')

    def activateCode(self):
        post_data = {
            'active': '',
            'backup': '',
            'sel_change_reason': '',
            'activated_sel[]': 'backup',
            'b_form1_submit': 'Apply',
            'b_form1_clicked': 'b_form1_submit'
        }
        self._httpPost('dual_image', post_data)

        post_data = {}
        try:
            self._httpPost('reboot', post_data, 0.5)
        except:
            print('Switch is rebooting, and the connection will be closed.')
            exit(0)

    def loopprotection(self):
        post_data = {
            'loop_protection_sel[]':'enabled',
            'transmission_time':'5',
            'shutdown_time':'180',
            'sorttable1_length':'10',
            'b_form1_submit':'Apply',
            'b_form1_clicked':'b_form1_submit'
        }
        self._httpPost('loop_protectiona',post_data)

        post_data = {
            'loop_protection_sel[]':'enabled',
            'action_sel[]':'shutdown_port',
            'tx_mode_sel[]':'enabled',
            'intf':'all',
            'b_modal1_clicked':'b_modal1_submit'
        }
        self._httpPost('loop_protectionb',post_data)

    def setmgmtvlan(self, vlan_id):
        post_data = {
            'protocol_type_sel[]':'dhcp',
            'session_timeout':'5',
            'mgmt_vlan_id_sel[]':vlan_id,
            'mgmt_port_sel[]':'none',
            'snmp_sel[]':'enabled',
            'community_name':'public',
            'b_form1_submit':'Apply',
            'change_mvlan':'yes',
            'change_mport':'no',
            'b_form1_clicked':'b_form1_submit'
        }
        self._httpPost('set_mgmt_vlan',post_data)

        post_data = {
            'protocol_type_sel[]':'dhcp',
            'session_timeout':'5',
            'mgmt_vlan_id_sel[]':vlan_id,
            'mgmt_port_sel[]':'none',
            'snmp_sel[]':'enabled',
            'community_name':'public',
            'b_form1_submit':'Apply',
            'change_mvlan':'no',
            'change_mport':'no',
            'b_form1_clicked':'b_form1_submit'
        }
        self._httpPost('set_mgmt_vlan',post_data)

    def downloadConfig(self, filepath):
        nowtime = int(1000 * time.time())
        post_data = {
            'file_type_sel[]': 'config',
            'http_token': nowtime
        }
        response = self._httpPost('file_upload', post_data)
        download_file = self._httpGet('file_download','?name=hp1820_8G.cfg&file=/mnt/download/hp1820_8G.cfg&token='+str(nowtime))
        try:
            f = open(filepath+'/hp1820_8G.cfg','w+')
            print('file downloaded to '+filepath+'/hp1820_8G.cfg')
            f.write(download_file)
        except PermissionError:
            print('permission denied.')
        except:
            print('error')
        self._httpGet('file_download','?name=hp1820_8G.cfg&file=/mnt/download/hp1820_8G.cfg&token='+str(nowtime)+'&remove=true')

    def setPortStatus(self, interface, status):
        post_data = {
            'admin_mode_sel[]': status, # enabled, disabled
            'phys_mode_sel[]': '1',
            'port_desc': '',
            'intf': interface,
            'b_modal1_clicked': 'b_modal1_submit'
        }
        self._httpPost('set_port_status', post_data)

    def setPortChannel(self, channel_id, interface_id_str, admin_mode, stp_mode, static_mode, clear = False):
        interface_ids = parseIds(interface_id_str)
        not_interface_ids = [i for i in range(1, 8 + 1) if i not in interface_ids]
        dstPortList = ''
        post_data = {
            'trunk_intf': str(53 + int(channel_id)),
            'trunk_name_input': 'TRK%s' % channel_id,
            'admin_mode_sel[]': admin_mode,
            'stp_mode_sel[]': stp_mode,
            'static_mode_sel[]': static_mode,
            'dot3adhash_sel[]': 'sda_vlan',
            'member_assoc_sel[]': not_interface_ids,
            'member_assoc_sel_selected[]': interface_ids,
            'dstPortList': dstPortList,
            'b_modal1_clicked': 'b_modal1_submit'
        }
        if interface_ids:
            post_data['member_assoc_sel_selected[]'] = interface_ids

        if clear:
            post_data['dstPortList'] = '1,2,3,4,5,6,7,8'

        self._httpPost('set_port_channel', post_data)

    def ping(self, ipAddr, count, interval, size):
        handle = 0

        post_data = {
            'handle': handle,
            'host_name_ipaddr': ipAddr,
            'count': count,
            'interval': interval,
            'size': size,
            'probessent': 1,
            'probefail': 1,
            'seq': -1,
            'done': 0,
            'stop_results': 0,
            'b_form1_clicked': 'b_form1_submit',
        }

        response = self._httpPost('ping', post_data)
        soup = BeautifulSoup(response, 'html.parser')
        handle = int(soup.select('#handle')[0]['value'])
        print('Pinging ' + ipAddr + ' with ' + str(size) + ' bytes of data:')

        self.seq = -1
        self.done = 0
        self.count = count
        self.probessent = 1
        self.probefail = 1
        while self.done == 0:
            time.sleep(0.15)
            self._ping_ajax(str(handle), ipAddr)


    # private method

    def _httpGet(self, operation, handle = ''):
        return httpRequest(self.session, 'GET', self._getUrl(operation)+handle)

    def _httpPost(self, operation, post_data, timeout = 0):
        return httpRequest(self.session, 'POST', self._getUrl(operation), post_data, None, timeout)

    def _httpPostFile(self, operation, post_data, files):
        return httpRequest(self.session, 'POST', self._getUrl(operation), post_data, files)

    def _getUrl(self, operation):
        return self.protocol + PROTOCOL_DELIMETER + self.host + URLS[operation]

    # This function is simply a translation of JS code
    def _ping_ajax(self, handle_val, host_name_ipaddr):
        res = self._httpGet('ping_ajax', handle_val)
        res = res.split('|')
        if res is not None:
            handle = int(res[0]);
            respip = res[1];
            rtt = int(res[2]);
            seq = int(res[3]);
            resptype = int(res[4]);
            operstatus = int(res[5]);
            sessionstate = int(res[6]);
            avgrtt = int(res[7]);
            maxrtt = int(res[8]);
            minrtt = int(res[9]);
            probesent = int(res[10]);
            proberesponse = int(res[11]);
            probefail = int(res[12]);
            
            if (not isnan(handle)) and handle != 0:
                results = ''
                if respip != host_name_ipaddr and respip != '0.0.0.0':
                    results = 'Reply from ' + respip + ': Destination Port Unreachable.'
                elif respip == host_name_ipaddr:
                    results = 'Reply from ' + respip + ': icmp_seq=' + str(seq) + ' time=' + str(rtt) + ' usec.'
                else:
                    results = 'Request Timed Out.'
                if probesent == self.count:
                    self.done = 1
                
                if respip != '' and seq != self.seq:
                    print(results)
                elif respip != '0.0.0.0' and respip != host_name_ipaddr and self.probessent < probesent:
                    print(results)
                elif probefail > 0 and self.probefail < probefail and self.probessent < probesent:
                    self.probefail = probefail
                    print('Request Timed Out.')
                if probesent == 0:
                    self.done = 1

                if operstatus == 0:
                    if self.done == 0:
                        self.done = 1
                        percent = 0
                        if probesent != 0:
                            percent = (probesent - proberesponse) * 100 / float(probesent)
                            print('---' + host_name_ipaddr + ' ping statistics----')
                            print(str(probesent) + ' packets transmitted, ' + str(proberesponse) + ' packets received, ' + str(percent) + '% packet loss')
                            print('round-trip (msec) min/avg/max = ' + str(minrtt) + '/' + str(avgrtt) + '/' + str(maxrtt))
                self.probessent = probesent
                self.seq = seq


URLS = {
    'login': '/htdocs/login/login.lua',
    'logout': '/htdocs/pages/main/logout.lsp',
    'factory_default': '/htdocs/pages/base/reset_cfg.lsp',
    'save_config': '/htdocs/lua/ajax/save_cfg.lua?save=1',
    'file_transfer': '/htdocs/lua/ajax/file_download_ajax.lua?protocol=6',
    'dashboard': '/htdocs/pages/base/dashboard.lsp',
    'mac_table': '/htdocs/pages/base/mac_address_table.lsp',
    'port_channel': '/htdocs/pages/switching/port_channel_summary.lsp',
    'all_config': '/htdocs/pages/base/support.lsp',
    'port_status': '/htdocs/pages/base/port_summary.lsp?tg=switch_port_config&showtab=1',
    'vlan_status': '/htdocs/pages/switching/vlan_status.lsp',
    'port_statistic': '/htdocs/pages/base/port_summary_stats.lsp',
    'add_vlan': '/htdocs/pages/switching/vlan_status_modal.lsp',
    'del_vlan': '/htdocs/pages/switching/vlan_status.lsp',
    'access_vlan': '/htdocs/pages/switching/vlan_per_port_modal.lsp',
    'set_port_status': '/htdocs/pages/base/port_summary_modal.lsp',
    'set_sysinfo': '/htdocs/pages/base/dashboard.lsp',
    'set_port_channel': '/htdocs/pages/switching/port_channel_modal.lsp',
    'set_network': '/htdocs/pages/base/network_ipv4_cfg.lsp',
    'set_timezone': '/htdocs/pages/base/timezone_cfg.lsp',
    'set_sntp': '/htdocs/pages/base/sntp_global_config.lsp',
    'set_account': '/htdocs/pages/base/user_accounts.lsp',
    'cert_state': '/htdocs/lua/ajax/https_cert_stat_ajax.lua',
    'https_config': '/htdocs/pages/base/https_cfg.lsp',
    'ping': '/htdocs/pages/base/ping.lsp',
    'ping_ajax': '/htdocs/lua/ajax/ping_ajax.lua?handle=',
    'file_upload': '/htdocs/lua/ajax/file_upload_ajax.lua?protocol=6',
    'file_download': '/htdocs/pages/base/file_http_download.lsp',
    'dual_image': '/htdocs/pages/base/dual_image_cfg.lsp',
    'reboot': '/htdocs/lua/ajax/sys_reset_ajax.lua?reset=1',
    'loop_protectiona':'/htdocs/pages/switching/loop_config.lsp',
    'loop_protectionb':'/htdocs/pages/switching/loop_config_modal.lsp',
    'set_mgmt_vlan':'/htdocs/pages/base/network_ipv4_cfg.lsp'
}

PROTOCOL_DELIMETER = "://"
TEST_CONNECTION_TIMEOUT = 5 # second

# private module function

def httpRequest(session, request_method, url, post_data = None, files = None, timeout = 0):
    # GET 
    if request_method == 'GET':
        return session.get(url, verify = False).text

    # POST:
    if files is None and timeout != 0:
        return session.post(url, post_data, verify = False, timeout = timeout).text
    elif files is None:
        return session.post(url, post_data, verify = False).text
    else:
        return session.post(url, post_data, files = files, verify = False).text

def parseIds(id_str):
    if '-' in id_str:
        start, end = [int(i) for i in id_str.split('-')]
        ids = list(range(start, end + 1))
    elif ',' in id_str:
        ids = [int(i) for i in id_str.split(',')]
    else:
        ids = []
    return ids

def showStatus(raw_response, first_row, ignore_first = True):
    printTable(first_row, parseStatus(raw_response, ignore_first))

def parseStatus(raw_response, ignore_first):
    string = regex.search('aDataSet = (.*)var aColumns', raw_response.replace('\n', '')).group(1)
    # swap single quote and double quote because jQuery format is not compatiblewith JSON
    string = string.replace("'", "`").replace('"', "'").replace("`", '"')
    string = string.rstrip().rstrip(';')
    obj = json.loads(string)
    return [i[1 if ignore_first else 0:] for i in obj]

# NOTE: The context of tds may be longer than th
def printTable(th, tds):
    padding = len(max(th, key=len)) + 1
    row_format = ("{:<%d}" % padding) * (len(th))
    print(row_format.format(*th))
    for row in tds:
        if len(row) == 0:
            continue
        print(row_format.format(*row))

def printDashboard(raw_response):
    html = BeautifulSoup(raw_response, 'html.parser')
    for row in html.find_all('tr'):
        cols = list(row.find_all('td'))
        if len(cols) == 4:
            print('Logged In User: Username/Connection From/Idle Time/Session Time')
            [print(i.get_text(), end='/') for i in cols]
            print()
        elif len(cols) == 2:
            (key, val) = (cols[0], cols[1])
            print(key.get_text(), end=': ')
            if val.input is not None: # print pre-fill value
                print(val.input['value'])
            else:
                print(val.get_text().replace('\n', ''))
