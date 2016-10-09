import requests
import json
import time
import re as regex
from bs4 import BeautifulSoup
import urllib.request, urllib.error, ssl

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
protocal = ""
host = ""
session = requests.Session()

def testConnection(protocal, host):
    url = protocal + PROTOCAL_DELIMETER + host
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        response = urllib.request.urlopen(url, timeout=5, context=ctx)
    except urllib.error.URLError as err:
        print("Cannot connect %s : %s" % (url, err.reason))
        return False

    return True

def connect(_protocal, _host):
    global host, protocal
    protocal, host = _protocal, _host

# DEPRECATED: This method uses the same API as showDashboard()
def getSwitchName():
    raw_response = httpGet('dashboard')
    html = BeautifulSoup(raw_response, 'html.parser')
    for row in html.find_all('tr'):
        cols = list(row.find_all('td'))
        if len(cols) == 2:
            (key, val) = (cols[0], cols[1])
            if key.get_text() == "System Name":
                return val.input['value']

def login(username, password):
    try:
        raw_response = httpPost('login', {'username': username, 'password': password})
        response = json.loads(raw_response)
    except requests.exceptions.ConnectionError:
        response = {'error': 'Connection error'}

    if response['error']:
        print('Cannot login: ' + response['error'])
        return False

    return True

def logout():
    httpGet('logout')
    print('Logout.')

def close():
    session.close()
    print('Session closed.')

def httpGet(operation):
    return session.get(protocal + PROTOCAL_DELIMETER + host + URLS[operation], verify=False).text

def httpPost(operation, post_data):
    return session.post(protocal + PROTOCAL_DELIMETER + host + URLS[operation], post_data, verify=False).text

def httpPostFile(operation, post_data, files):
    return session.post(protocal + PROTOCAL_DELIMETER + host + URLS[operation], post_data, files = files, verify=False).text

def printTable(th, tds):
    padding = len(max(th, key=len)) + 1
    row_format = ("{:<%d}" % padding) * (len(th))
    print(row_format.format(*th))
    for row in tds:
        if len(row) == 0: 
            continue
        print(row_format.format(*row))

def showDashboard():
    raw_response = httpGet('dashboard')
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

def showPortStatus():
    raw_response = httpGet('port_status')
    data = parseStatus(raw_response)
    first_row = ['Interface','Admin Mode','Physical Type','Port Status','Physical Mode','Link Speed','MTU']
    printTable(first_row, data)

def showPortChannel():
    raw_response = httpGet('port_channel')
    data = parseStatus(raw_response)
    first_row = ['Interface', 'Name', 'Type', 'Admin Mode', 'Link Status', 'Members', 'Active Ports']
    printTable(first_row, data)

def showMacTable():
    raw_response = httpGet('mac_table')
    data = parseStatus(raw_response, ignore_first = False)
    first_row = ['VLAN ID', 'MAC Address', 'Interface', 'Interface Index', 'Status']
    printTable(first_row, data)

def parseStatus(raw_response, ignore_first = True):
    string = regex.search('aDataSet = (.*)var aColumns', raw_response.replace('\n', '')).group(1)
    # swap single quote and double quote because jQuery format is not compatiblewith JSON
    string = string.replace("'", "`").replace('"', "'").replace("`", '"')
    string = string.rstrip().rstrip(';')
    obj = json.loads(string)
    return [i[1 if ignore_first else 0:] for i in obj]

def showVlanStatus():
    raw_response = httpGet('vlan_status')
    data = parseStatus(raw_response)
    first_row = ['VLAN ID', 'Name', 'Type']
    printTable(first_row, data)

def showPortStatistic():
    raw_response = httpGet('port_statistic')
    data = parseStatus(raw_response, ignore_first = False)
    first_row = ['Int','RX w/o Err','RX with Err','RX Broadcast','TX w/o Err','TX with Err','Collision','TX PauseFrame','RX PauseFrame']
    printTable(first_row, data)


def setSystemInfo(name, loc, con):
    post_data = {'sys_name': name, 'sys_location': loc, 'sys_contact': con, 'b_form1_submit': 'Apply', 'b_form1_clicked': 'b_form1_submit'}
    httpPost('set_sysinfo', post_data)

def setNetwork(mode, ip = '', subnet = '', gateway = '', mgmt_vlan = '1'):
    required_data = {
        'protocol_type_sel[]': mode,  #static or dhcp
        'session_timeout': '3',
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
    httpPost('set_network', post_data)

def setAccount(username, old_pwd, new_pwd, confirm_new_passwd):
    post_data = {
        'user_name': username,
        'current_password': old_pwd,
        'new_password': new_pwd,
        'confirm_new_passwd': new_pwd,
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    response = httpPost('set_account', post_data)
    if 'Required field' in response:
        print("Cannot update password, required field is not valid")
    elif 'password is incorrect' in response:
        print("Cannot update password, current password is incorrect")
    else:
        print("Username/Password changed successfully")

def setTimezone():
    post_data = {
        'offset_sel[]': '77',
        'zone': 'TPE',
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    httpPost('set_timezone', post_data)

def setSntp(sntp_ip):
    post_data = {
        'set_sys_time_sel[]': 'using_sntp',
        'client_mode_sel[]': 'enabled',
        'host_name_ipaddr': sntp_ip,
        'server_port': '123',
        'date_alt': '1970-1-1',
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    httpPost('set_sntp', post_data)

def showVlanPort():
    raw_response = httpGet('all_config')
    html = BeautifulSoup(raw_response, 'html.parser')
    first_row = ['VLAN ID', 'Tagged Ports', 'Untagged Ports', 'Exclude Participation']
    data = []
    for table in html.find_all("table"):
        if table["id"] != "sorttable12":
            continue
        for row in table.find_all("tr"):
            data.append([col.get_text() for col in row.find_all("td")])
    printTable(first_row, data)

def accessVlan(mode, interfaces, vlan_id):
    post_data = {
        'part_tagg_sel[]': mode, # tagged, untagged, exclude
        'vlan': vlan_id,
        'intfStr': interfaces, # 1-8, TRK1: 54, TRK2: 55 ...
        'part_exclude': 'yes',
        'parentQStr': '?vlan=%s' % vlan_id, # looks like this doesn't matter
        'b_modal1_clicked': 'b_modal1_submit'
    }
    httpPost('access_vlan', post_data)

# @param example: 5-18 or 7 or 1,4,7
def addVlan(vlan_id_str):
    post_data = {
        'vlan_id_range': vlan_id_str,
        'vlancount': '1',
        'b_modal1_clicked': 'b_modal1_submit'
    }
    httpPost('add_vlan', post_data)

# @param example: 5-18 or 7 or 1,4,7
def delVlan(vlan_id_str):
    vlan_ids = parseIds(vlan_id_str)
    post_data = {
        'sorttable1_length': '-1',
        'chkrow[]': vlan_ids,
        'b_form1_clicked': 'b_form1_dt_remove'
    }
    httpPost('del_vlan', post_data)

# Generate https SSL certificate.
def genCert():
    post_data = {
        'http_mode_sel[]': 'enabled',
        'https_mode_sel[]': 'disabled',
        'soft_timeout': '5',
        'hard_timeout': '24',
        'certificate_stat': 'Absent',
        'b_form1_clicked': 'b_form1_bt_generate'
    }
    httpPost('https_config', post_data)
    while httpGet('cert_state') != 'Present':
        time.sleep(1)

# set the management interface
# @param "enabled", "disabled"
def setHttps(http, https):
    post_data = {
        'http_mode_sel[]': http,
        'https_mode_sel[]': https,
        'soft_timeout': '5',
        'hard_timeout': '24',
        'certificate_stat': 'Present',
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    httpPost('https_config', post_data)

def saveConfig():
    httpPost('save_config', {})

def reset():
    httpPost('factory_default', {"b_form1_clicked": "b_form1_reset"})

# Upload config file. The filename should be hp1820_8G.cfg. Other names are deprecated.
def uploadConfig(filepath):
    post_data = {
        'file_type_sel[]': 'config',
        'orig_file_name': 'hp1820_8G.cfg',
        'optDSV': '1',
        'filename': 'hp1820_8G.cfg',
        'transfer_file': 'hp1820_8G.cfg'
    }
    files = {'transfer_file': open(filepath, 'rb')}
    httpPostFile('file_transfer', post_data, files)

def setPortStatus(interface, status):
    post_data = {
        'admin_mode_sel[]': status, # enabled, disabled
        'phys_mode_sel[]': '1',
        'port_desc': 'port_descr',
        'intf': interface,
        'b_modal1_clicked': 'b_modal1_submit'
    }
    httpPost('set_port_status', post_data)

def setPortChannel(channel_id, interface_id_str, admin_mode, stp_mode, static_mode, clear = False):
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

    httpPost('set_port_channel', post_data)

def parseIds(id_str):
    if not id_str:
        return []
    if '-' in id_str:
        start, end = [int(i) for i in id_str.split('-')]
        ids = list(range(start, end + 1))
    else:
        ids = [int(i) for i in id_str.split(',')]
    return ids
