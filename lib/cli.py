import requests
import json
import time
import re as regex
from bs4 import BeautifulSoup
import urllib.request, urllib.error, ssl

class Cli:
    def __init__(self, protocol, host):
        self.protocol, self.host = protocol, host
        self.session = requests.Session()

    @staticmethod
    def testConnection(protocol, host):
        url = protocol + PROTOCAL_DELIMETER + host
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

    def showVlanMembership(self):
        printVlanMembership(self._httpGet('all_config'))

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
            'b_form1_clicked': 'b_form1_submit'
        }
        if mode == "static":
            ip_data = {
                'ip_addr': ip,
                'subnet_mask': subnet,
                'gateway_address': gateway
            }
            post_data = {**ip_data,  **required_data}
        else:
            post_data = required_data
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

    # @param example: 5-18 or 7 or 1,4,7
    def addVlan(self, vlan_id_str):
        post_data = {
            'vlan_id_range': vlan_id_str,
            'vlancount': '1',
            'b_modal1_clicked': 'b_modal1_submit'
        }
        self._httpPost('add_vlan', post_data)

    # @param example: 5-18 or 7 or 1,4,7
    def delVlan(self, vlan_id_str):
        vlan_ids = parseIds(vlan_id_str)
        post_data = {
            'sorttable1_length': '-1',
            'chkrow[]': vlan_ids,
            'b_form1_clicked': 'b_form1_dt_remove'
        }
        self._httpPost('del_vlan', post_data)

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

    def setPortStatus(self, interface, status):
        post_data = {
            'admin_mode_sel[]': status, # enabled, disabled
            'phys_mode_sel[]': '1',
            'port_desc': 'port_descr',
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

    # private method

    def _httpGet(self, operation):
        return httpRequest(self.session, 'GET', self._getUrl(operation))

    def _httpPost(self, operation, post_data):
        return httpRequest(self.session, 'POST', self._getUrl(operation), post_data)

    def _httpPostFile(self, operation, post_data, files):
        return httpRequest(self.session, 'POST', self._getUrl(operation), post_data, files)

    def _getUrl(self, operation):
        return self.protocol + PROTOCAL_DELIMETER + self.host + URLS[operation]

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
    'https_config': '/htdocs/pages/base/https_cfg.lsp'
}

PROTOCAL_DELIMETER = "://"
TEST_CONNECTION_TIMEOUT = 5 # second

# private module function

def httpRequest(session, request_method, url, post_data = None, files = None):
    # GET 
    if request_method == 'GET':
        return session.get(url, verify = False).text

    # POST:
    if files is None:
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

def printVlanMembership(raw_response):
    html = BeautifulSoup(raw_response, 'html.parser')
    first_row = ['VLAN ID', 'Tagged Ports', 'Untagged Ports', 'Exclude Participation']
    data = []
    for table in html.find_all("table"):
        if table["id"] != "sorttable12":
            continue
        for row in table.find_all("tr"):
            data.append([col.get_text() for col in row.find_all("td")])
    printTable(first_row, data)
