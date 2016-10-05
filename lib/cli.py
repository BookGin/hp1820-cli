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
    'all_config': '/htdocs/pages/base/support.lsp',
    'port_status': '/htdocs/pages/base/port_summary.lsp?tg=switch_port_config&showtab=1',
    'vlan_status': '/htdocs/pages/switching/vlan_status.lsp',
    'add_vlan': '/htdocs/pages/switching/vlan_status_modal.lsp',
    'del_vlan': '/htdocs/pages/switching/vlan_status.lsp',
    'access_vlan': '/htdocs/pages/switching/vlan_per_port_modal.lsp',
    'set_sysinfo': '/htdocs/pages/base/dashboard.lsp',
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

def printTable(th, td)
    padding = len(max(th, key=len)) + 1
    row_format = ("{:<%d}" % padding) * (len(th))
    print(row_format.format(*tr))
    for row in tds:
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

def showMacTable():
    raw_response = httpGet('mac_table')
    data = parseStatus(raw_response, ignore_first = False)
    first_row = ['VLAN ID', 'MAC Address', 'Interface', 'Interface Index', 'Status']
    print(first_row, data)

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

def addVlan(vlan_id_range):
    post_data = {
        'vlan_id_range': vlan_id_range,
        'vlancount': '1',
        'b_modal1_clicked': 'b_modal1_submit'
    }
    httpPost('add_vlan', post_data)

def delVlan(vlan_id):
    #TODO: delete Multiple vlan, but this is a dict, chkrow[] cannot have multi value
    post_data = {
        'sorttable1_length': '-1',
        'chkrow[]': vlan_id,
        #'chkrow[]': '11',
        'b_form1_clicked': 'b_form1_dt_remove'
    }
    httpPost('del_vlan', post_data)

def accessVlan(mode, interfaces, vlan_id):
    post_data = {
        'part_tagg_sel[]': mode, # tagged, untagged, exclude
        'vlan': vlan_id,
        'intfStr': interfaces, # 5,6,7,8
        'part_exclude': 'yes',
        'parentQStr': '?vlan=%s' % vlan_id, # looks like this doesn't matter
        'b_modal1_clicked': 'b_modal1_submit'
    }
    httpPost('access_vlan', post_data)

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

def uploadConfig(filepath):
    post_data = {
        'file_type_sel[]': 'config',
        'orig_file_name': 'hp1820_8G.cfg',
        'optDSV': '1',
        'filename': 'hp1820_8G.cfg',
        'transfer_file': 'hp1820_8G.cfg'
    }
    files = {
        'transfer_file': open(filepath, 'rb')
    }
    httpPostFile('file_transfer', post_data, files)

if __name__ == "__main__":
    connect("http", "192.168.1.1")
    login("admin", "password")
    try:
        showMacTable()
        showDashboard()
        showPortStatus()
        showVlanStatus()
        setSystemInfo("SwitchName", "Location", "Contact")
        #setNetwork()
        addVlan("9-11")
        showVlanStatus()
        showVlanPort()
        delVlan("10")
        accessVlan("untagged", "5,6,7,8", "11") # interfaces, vlan id
        #setAccount("admin", "password", "password", "password")
        logout()
        session.close()
    except Exception as e:
        print(e)
        logout()
        session.close()

