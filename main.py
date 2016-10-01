import requests
import json
from bs4 import BeautifulSoup
URLS = {
        'login': 'http://192.168.1.1/htdocs/login/login.lua',
        'logout': 'http://192.168.1.1/htdocs/pages/main/logout.lsp',
        'dashboard': 'http://192.168.1.1/htdocs/pages/base/dashboard.lsp',
        'port_status': 'http://192.168.1.1/htdocs/pages/base/port_summary.lsp?tg=switch_port_config&showtab=1',
        'set_sysinfo': 'http://192.168.1.1/htdocs/pages/base/dashboard.lsp',
        'set_network': 'http://192.168.1.1/htdocs/pages/base/network_ipv4_cfg.lsp'

}
def logout():
    session.get(URLS['logout'])

def login():
    postdata = {'username': 'admin',  'password': ''}
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

def parsePortStatus(raw_response):
    html = BeautifulSoup(raw_response, 'html.parser')
    data = list(html.find_all('script'))[8].get_text()
    lines = data.split('\n')
    string = ''.join(lines[3:28]).rstrip(';').replace('var aDataSet = ', '')
    # swap single quote and double quote because jQuery format is not compatiblewith JSON
    string = string.replace("'", "`").replace('"', "'").replace("`", '"')
    obj = json.loads(string)
    return [i[1:] for i in obj]

def showPortStatus():
    raw_response = session.get(URLS['port_status']).text
    data = parsePortStatus(raw_response)
    print(['Interface','Admin Mode','Physical Type','Port Status','Physical Mode','Link Speed','MTU'])
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



session = requests.Session()
login()
try:
    showDashboard()
    showPortStatus()
    setSystemInfo("SwitchName", "Location", "Contact")
    setNetwork()
    logout()
    session.close()
except Exception as e:
    print(e)
    logout()
    session.close()
