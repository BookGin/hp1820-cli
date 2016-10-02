from cmd import Cmd
from getpass import getpass
import cli

class Prompt(Cmd):
    def do_exit(self, args):
        """Logout current switch and exit."""
        cli.logout()
        cli.close()
        raise SystemExit

    def do_showrun(self, args):
        cli.showDashboard()

    def do_showint(self, args):
        cli.showPortStatus()

    def do_showvlan(self, args):
        cli.showVlanStatus()
        cli.showVlanPort()

    def do_showmac(self, args):
        cli.showMacTable()

    def do_setinfo(self, args):
        cli.setSystemInfo(input("Switch Name: "), input("Location: "), input("Contact: "))
        prompt.prompt = '%s#' % cli.getSwitchName()

    def do_write(self, args):
        """Save configuration."""
        cli.saveConfig()

    def do_setaccount(self, args):
        user, cur_pwd, new_pwd, confirm_pwd = input("New username: "), getpass("Current password: "), getpass("New password: "), getpass("Retype new password: ")
        if new_pwd != confirm_pwd:
            print("Confirm password is different.")
        else:
            cli.setAccount(user, cur_pwd, new_pwd, confirm_pwd)

    def do_setnetwork(self, args):
        manage_vlan_id = input("management vlan id? (empty = 1)")
        manage_vlan_id = '1' if manage_vlan_id == '' else manage_vlan_id
        mode = input("dhcp or static?")
        while mode != "static" and mode != "dhcp":
            mode = input("dhcp or static?")
        cli.setNetwork(mode, input("(if dhcp, left empty below) IP: "), input("subnet mask: "), input("gateway address: "), manage_vlan_id)

    def do_settime(self, args):
        cli.setTimezone()
        print("Automatically set timezone to GMT+8(TPE) successfully.")
        cli.setSntp(input("SNTP IP address: "))

    def do_vlanadd(self, args):
        """vlanadd VLAN_ID"""
        if len(args) == 0: print("need argument"); return
        cli.addVlan(args)

    def do_vlandel(self, args):
        """vlandel VLAN_ID"""
        if len(args) == 0: print("need argument"); return
        cli.delVlan(args)

    def do_vlanset(self, args):
        available_mode = {'t':'tagged', 'u':'untagged', 'e':'exclude'}
        mode = input("tagged[t]/untagged[u]/exclude[e]?")
        while mode not in available_mode:
            mode = input("tagged[t]/untagged[u]/exclude[e]?")
        cli.accessVlan(available_mode[mode], input("Interfaces(1-8)?"), input("Vlan id?"))

    def do_gencert(self, args):
        print("Generating a new cert...")
        cli.genCert()

    def do_sethttps(self, args):
        print("Note: If the new protocal is different from current one, you have to login again.")
        available_choice = {'http': ('enabled', 'disabled'), 'https':('disabled', 'enabled'), 'both':('enabled', 'enabled')}
        choice = input("http only[http]/https only[https]/both[both]?")
        while choice not in available_choice:
            choice = input("http only[http]/https only[https]/both[both]?")
        cli.setHttps(available_choice[choice][0], available_choice[choice][1])

prompt = Prompt()

def run():
    prompt.prompt = '%s#' % cli.getSwitchName()
    while True:
        try:
            prompt.cmdloop('Type exit to quit, help for help.')
        except KeyboardInterrupt:
            pass
        except AttributeError as e:
            print("An error occured: " + e)
            print("Maybe the session is timeout?")
            raise SystemExit
