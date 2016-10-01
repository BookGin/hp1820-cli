import requests
import json
import re as regex
from bs4 import BeautifulSoup
URLS = {
        'login': 'http://192.168.1.1/htdocs/login/login.lua',
        'logout': 'http://192.168.1.1/htdocs/pages/main/logout.lsp',
        'dashboard': 'http://192.168.1.1/htdocs/pages/base/dashboard.lsp',
        'all_config': 'http://192.168.1.1/htdocs/pages/base/support.lsp',
        'port_status': 'http://192.168.1.1/htdocs/pages/base/port_summary.lsp?tg=switch_port_config&showtab=1',
        'vlan_status': 'http://192.168.1.1/htdocs/pages/switching/vlan_status.lsp',
        'add_vlan': 'http://192.168.1.1/htdocs/pages/switching/vlan_status_modal.lsp',
        'del_vlan': 'http://192.168.1.1/htdocs/pages/switching/vlan_status.lsp',
        'access_vlan': 'http://192.168.1.1/htdocs/pages/switching/vlan_per_port_modal.lsp',
        'set_sysinfo': 'http://192.168.1.1/htdocs/pages/base/dashboard.lsp',
        'set_network': 'http://192.168.1.1/htdocs/pages/base/network_ipv4_cfg.lsp',
        'set_account': 'http://192.168.1.1/htdocs/pages/base/user_accounts.lsp'

}
def logout():
    session.get(URLS['logout'])

def login(username, password):
    postdata = {'username': username,  'password': password}
    raw_response = session.post(URLS['login'], data = postdata).text
    response = json.loads(raw_response)
    if response['error']:
        raise RuntimeError('Cannot login: ' + response['error'])
    print('Login successful!')

def showDashboard():
    raw_response = session.get(URLS['dashboard']).text
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
    raw_response = session.get(URLS['port_status']).text
    data = parseStatus(raw_response)
    print(['Interface','Admin Mode','Physical Type','Port Status','Physical Mode','Link Speed','MTU'])
    print(*data, sep='\n')

def parseStatus(raw_response):
    string = regex.search('aDataSet = (.*)var aColumns', raw_response.replace('\n', '')).group(1)
    # swap single quote and double quote because jQuery format is not compatiblewith JSON
    string = string.replace("'", "`").replace('"', "'").replace("`", '"')
    string = string.rstrip().rstrip(';')
    obj = json.loads(string)
    return [i[1:] for i in obj]

def showVlanStatus():
    raw_response = session.get(URLS['vlan_status']).text
    data = parseStatus(raw_response)
    print(['VLAN ID', 'Name', 'Type'])
    print(*data, sep='\n')

def setSystemInfo(name, loc, con):
    postdata = {'sys_name': name, 'sys_location': loc, 'sys_contact': con, 'b_form1_submit': 'Apply', 'b_form1_clicked': 'b_form1_submit'}
    session.post(URLS['set_sysinfo'], data = postdata)

def setNetwork():
    postdata = {'protocol_type_sel[]': 'static', # or dhcp
        'ip_addr': '192.168.1.1',
        'subnet_mask': '255.255.255.0',
        'gateway_address': '192.168.1.87',

        'session_timeout': '3',
        'mgmt_vlan_id_sel[]': '1',
        'mgmt_port_sel[]': 'none',
        'snmp_sel[]': 'enabled',
        'community_name': 'public',
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    session.post(URLS['set_network'], data = postdata)

def setAccount(username, old_pwd, new_pwd):
    postdata = {
        'user_name': username,
        'current_password': old_pwd,
        'new_password': new_pwd,
        'confirm_new_passwd': new_pwd,
        'b_form1_submit': 'Apply',
        'b_form1_clicked': 'b_form1_submit'
    }
    response = session.post(URLS['set_account'], data = postdata).text
    if 'Required field' in response:
        print("Cannot update password, required field is not valid")
    elif 'password is incorrect' in response:
        print("Cannot update password, current password is incorrect")
    else:
        print("Username/Password changed successfully")


def addVlan(vlan_id_range):
    postdata = {
        'vlan_id_range': vlan_id_range,
        'vlancount': '1',
        'b_modal1_clicked': 'b_modal1_submit'
    }
    session.post(URLS['add_vlan'], data = postdata)

def delVlan(vlan_id):
    #TODO: delete Multiple vlan, but this is a dict, chkrow[] cannot have multi value
    postdata = {
        'sorttable1_length': '-1',
        'chkrow[]': vlan_id,
        #'chkrow[]': '11',
        'b_form1_clicked': 'b_form1_dt_remove'
    }
    session.post(URLS['del_vlan'], data = postdata)

def accessVlan(mode, interfaces, vlan_id):
    postdata = {
        'part_tagg_sel[]': mode, # tagged, untagged
        'vlan': vlan_id,
        'intfStr': interfaces, # 5,6,7,8
        'part_exclude': 'yes',
        'parentQStr': '?vlan=%s' % vlan_id,
        'b_modal1_clicked': 'b_modal1_submit'
    }
    session.post(URLS['access_vlan'], data = postdata)

def showVlanPort():
    raw_response = session.get(URLS['all_config']).text
    html = BeautifulSoup(raw_response, 'html.parser')
    print("VLAN ID / Tagged Ports  /  Untagged Ports / Exclude Participation")
    for table in html.find_all("table"):
        if table["id"] != "sorttable12":
            continue
        for row in table.find_all("tr"):
            [print(col.get_text(), end="   /") for col in row.find_all("td")]
            print()


session = requests.Session()
login("admin", "password")
try:
    showDashboard()
    showPortStatus()
    showVlanStatus()
    setSystemInfo("SwitchName", "Location", "Contact")
    setNetwork()
    addVlan("9-11")
    showVlanStatus()
    showVlanPort()
    delVlan("10")
    accessVlan("untagged", "5,6,7,8", "11") # interfaces, vlan id
    #setAccount("admin", "password", "password")
    logout()
    session.close()
except Exception as e:
    print(e)
    logout()
    session.close()
