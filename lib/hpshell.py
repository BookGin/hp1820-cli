from cmd import Cmd
from getpass import getpass
from lib import cli

class Prompt(Cmd):
    def do_forceexit(self, args):
        """Quit the program without logout."""
        raise SystemExit

    def do_EOF(self, args):
        """Logout current switch and exit."""
        print("Type exit to quit.")

    def do_exit(self, args):
        """Logout current switch and exit."""
        cli.logout()
        cli.close()
        raise SystemExit

    def do_showrun(self, args):
        """Show switch dashboard information."""
        cli.showDashboard()

    def do_showint(self, args):
        """Show interfaces status."""
        cli.showPortStatus()

    def do_showvlan(self, args):
        """Show VLAN status."""
        cli.showVlanStatus()
        cli.showVlanPort()

    def do_showmac(self, args):
        """Show mac address table."""
        cli.showMacTable()

    def do_setinfo(self, args):
        """Set switch name, Location, contact."""
        cli.setSystemInfo(input("Switch Name: "), input("Location: "), input("Contact: "))
        prompt.prompt = '%s#' % cli.getSwitchName()

    def do_write(self, args):
        """Save configuration."""
        cli.saveConfig()

    def do_setaccount(self, args):
        """Modify administrative account."""
        user, cur_pwd, new_pwd, confirm_pwd = input("New username: "), getpass("Current password: "), getpass("New password: "), getpass("Retype new password: ")
        if new_pwd != confirm_pwd:
            print("Confirm password is different.")
        else:
            cli.setAccount(user, cur_pwd, new_pwd, confirm_pwd)

    def do_setnetwork(self, args):
        """Set switch IP, subnet, gateway, management vlan."""
        manage_vlan_id = input("management vlan id? (empty = 1)")
        manage_vlan_id = '1' if manage_vlan_id == '' else manage_vlan_id
        mode = input("dhcp or static?")
        while mode != "static" and mode != "dhcp":
            mode = input("dhcp or static?")
        cli.setNetwork(mode, input("(if dhcp, left empty below) IP: "), input("subnet mask: "), input("gateway address: "), manage_vlan_id)

    def do_settime(self, args):
        """Set SNTP server IP and timezone (support GMT+8 TPE only)."""
        cli.setTimezone()
        print("Automatically set timezone to GMT+8(TPE) successfully.")
        cli.setSntp(input("SNTP IP address: "))

    def do_vlanadd(self, args):
        """Add a new vlan interface."""
        cli.addVlan(input("'-' to specify a range and ',' to separate VLAN ID\nAdd vlan id (2 to 4093)? "))

    def do_vlandel(self, args):
        """Delete a new vlan interface."""
        cli.delVlan(input("'-' to specify a range and ',' to separate VLAN ID\nDelete vlan id (2 to 4093)? "))

    def do_vlanset(self, args):
        """Set interfaces vlan membership."""
        available_mode = {'t':'tagged', 'u':'untagged', 'e':'exclude'}
        mode = input("tagged[t]/untagged[u]/exclude[e]?")
        while mode not in available_mode:
            mode = input("tagged[t]/untagged[u]/exclude[e]?")
        cli.accessVlan(available_mode[mode], input("Interfaces(1-8), TRK1-4 (54-57)?"), input("Vlan id?"))

    def do_gencert(self, args):
        """Generate a new self-signed SSL certificate."""
        print("Generating a new cert...")
        cli.genCert()

    def do_sethttps(self, args):
        """Set management connection protocal (HTTP or HTTPS)."""
        print("Note: If the new protocal is different from current one, you have to login again.")
        available_choice = {'http': ('enabled', 'disabled'), 'https':('disabled', 'enabled'), 'both':('enabled', 'enabled')}
        choice = input("http only[http]/https only[https]/both[both]?")
        while choice not in available_choice:
            choice = input("http only[http]/https only[https]/both[both]?")
        cli.setHttps(available_choice[choice][0], available_choice[choice][1])

    def do_reset(self, args):
        """Restore to factory configuration."""
        print("Note: After resetting, you have to save configuration to apply factory default when rebooting.")
        choice = input("Restore to factory configuration?(y/n)")
        while choice not in "yn":
            choice = input("Restore to factory configuration?(y/n)")
        if choice == 'y':
            cli.reset()

    def do_uploadconfig(self, args):
        """Upload a config file to switch."""
        cli.uploadConfig(input('config file location?(absolute path)'))

    def do_setportchannel(self, args):
        """Configure port channel settings."""
        available_mode = {'y':'enabled', 'n':'disabled'}
        stp_mode = input("stp_mode (y/n)?")
        while stp_mode not in available_mode:
            stp_mode = input("stp_mode (y/n)?")
        static_mode = input("static_mode (y/n)?")
        while static_mode not in available_mode:
            static_mode = input("static_mode (y/n)?")
        cli.setPortChannel(input("channel id (1-4)? "), input("member interface ?"), 'enabled', stp_mode, static_mode)

    def do_clearportchannel(self, args):
        """Clear port channel settings."""
        cli.setPortChannel(input("channel id (1-4)? "), '', 'enabled', 'enabled', 'enabled', clear=True)

    def do_setportstatus(self, args):
        """Enable or disable ports."""
        available_mode = {'e':'enabled', 'd':'disabled'}
        mode = input("enable or disable a port(e/d)?")
        while mode not in available_mode:
            mode = input("enable or disable a port(e/d)?")
        cli.setPortStatus(input("Interfaces(1-8), TRK1-4 (54-57)?"), mode)

prompt = Prompt()

def run():
    prompt.prompt = '%s#' % cli.getSwitchName()
    while True:
        try:
            prompt.cmdloop('Type exit to quit, help for help.')
        except KeyboardInterrupt:
            pass
        #except Exception as e:
        #    print("An error occured: " + str(e))
        #    print("Maybe the session is timeout?")
        #    raise SystemExit
