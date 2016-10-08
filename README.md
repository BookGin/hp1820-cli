# HP 1820 command-line Interface 

A command line interface for HP 1820 J9979A switch. 

HP 1820 J9979A only provides web management interface. This is awkward for network administrators familiar with Cisco IOS interface. Therefore, this project is the solution to encapsulate the two different management layer.

## A Quick View
```sh
$ ./sshhp 192.168.1.1
Cannot connect https://192.168.1.1 : [Errno 111] Connection refused
HTTPS failed. Try HTTP...
*****************************************
*Warning: Connect through HTTP protocal.*
*****************************************
Password: 
Type exit/forceexit to quit, help for help.

#setnetwork
management vlan id? (empty = 1)
dhcp or static?static
(if dhcp, left empty below) IP: 192.168.1.1
subnet mask: 255.255.255.0
gateway address: 

#setinfo
Switch Name: new-switch
Location: here
Contact: bookgin

new-switch#showint
Interface     Admin Mode    Physical Type Port Status   Physical Mode Link Speed    MTU           
1             Enabled       Normal        Link Up       Auto          100 Mbps Full Duplex1518          
2             Enabled       Normal        Link Down     Auto                        1518          
3             Enabled       Normal        Link Down     Auto                        1518          
4             Enabled       Normal        Link Down     Auto                        1518          
5             Enabled       Normal        Link Down     Auto                        1518          
6             Enabled       Normal        Link Down     Auto                        1518          
7             Enabled       Normal        Link Down     Auto                        1518          
8             Disabled      Normal        Link Down     Auto                        1518          
TRK1          Disabled      Normal        Link Down     Trunk                       1518          
TRK2          Enabled       Normal        Link Down     Trunk                       1518          
TRK3          Enabled       Normal        Link Down     Trunk                       1518          
TRK4          Enabled       Normal        Link Down     Trunk                       1518          

new-switch#
Logout.
Session closed.
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

- [x] Port channel 
- [ ] Prettify the information output
- [ ] Ping Test (Need to handle jsvascript)
- [ ] Download current config file (Need to handle javascript)
