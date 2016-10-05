# HP 1820 command-line Interface 

A command line interface for HP 1820 J9979A switch. 

HP 1820 J9979A only provide web management interface. This is awkward for network administrators who are very familiar with Cisco IOS interface. Therefore, this project is the solution to encapsulate the two different management layer.

## A Quick View
```sh
$ ./sshhp admin@192.168.1.1
Password: 

Type exit to quit, help for help.
#help

Documented commands (type help <topic>):
========================================
exit  help  vlanadd  vlandel  write

Undocumented commands:
======================
gencert     sethttps  setnetwork  showint  showrun   vlanset
setaccount  setinfo   settime     showmac  showvlan

#showint
['Interface', 'Admin Mode', 'Physical Type', 'Port Status', 'Physical Mode', 'Link Speed', 'MTU']
['1', 'Enabled', 'Mirrored', 'Link Down', 'Auto', '', '1518']
['2', 'Enabled', 'Normal', 'Link Up', 'Auto', '100 Mbps Full Duplex', '1518']
['3', 'Enabled', 'Normal', 'Link Down', 'Auto', '', '1518']
['4', 'Enabled', 'Normal', 'Link Down', 'Auto', '', '1518']
['5', 'Enabled', 'Normal', 'Link Down', 'Auto', '', '1518']
['6', 'Enabled', 'Normal', 'Link Down', 'Auto', '', '1518']
['7', 'Enabled', 'Normal', 'Link Down', 'Auto', '', '1518']
['8', 'Enabled', 'Probe', 'Link Down', 'Auto', '', '1518']
['TRK1', 'Enabled', 'Normal', 'Link Down', 'Trunk', '', '1518']
['TRK2', 'Enabled', 'Normal', 'Link Down', 'Trunk', '', '1518']
['TRK3', 'Enabled', 'Normal', 'Link Down', 'Trunk', '', '1518']
['TRK4', 'Enabled', 'Normal', 'Link Down', 'Trunk', '', '1518']

#setinfo
Switch Name: new_switch
Location: my_home
Contact: bookgin
new_switch#set
setaccount  sethttps    setinfo     setnetwork  settime     

new_switch#setnetwork
management vlan id? (empty = 1)
dhcp or static?static
(if dhcp, left empty below) IP: 192.168.1.1
subnet mask: 255.255.255.0
gateway address: 
new_switch#
```
## Install

You may have to install [BeautifulSoup4](https://pypi.python.org/pypi/beautifulsoup4) first.

```
$ git clone https://github.com/BookGin/hp1820-cli.git
$ cd hp1820-cli/
$ ./sshhp admin@192.168.1.1
```

## Dependency

- Python 3.5
- [requests 2.11.1](https://pypi.python.org/pypi/requests)
- [BeautifulSoup4 4.5.1](https://pypi.python.org/pypi/beautifulsoup4)

## Unimplemented Features

- [x] Prettify the information output
- [ ] Port channel 
- [ ] Ping Test
- [ ] Download current config file
