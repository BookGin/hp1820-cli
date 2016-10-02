from cmd import Cmd
from getpass import getpass
import cli

class Prompt(Cmd):
    def do_exit(self, args):
        """Logout current switch and exit."""
        cli.logout()
        cli.close()
        raise SystemExit

    def do_show(self, args):
        if args == "ru" or args == "run":
            cli.showDashboard()
        elif args == "int":
            cli.showPortStatus()
        elif args == "vlan":
            cli.showVlanStatus()
            cli.showVlanPort()

    def do_setinfo(self, args):
        cli.setSystemInfo(input("Switch Name: "), input("Location: "), input("Contact: "))
        prompt.prompt = '%s#' % cli.getSwitchName()

    def do_write(self, args):
        """Save configuration."""
        cli.saveConfig()

    def do_setaccount(self, args):
        cli.setAccount(input("New username: "), getpass("Current password: "), getpass("New password: "), getpass("Retype new password: "))

    def do_setnetwork(self, args):
        mode = input("dhcp or static?")
        while mode != "static" and mode != "dhcp":
            mode = input("dhcp or static?")
        cli.setNetwork(mode, input("(if dhcp, left empty below) IP: "), input("subnet mask: "), input("gateway address: "))

prompt = Prompt()

def run():
    prompt.prompt = '%s#' % cli.getSwitchName()
    while True:
        try:
            prompt.cmdloop('Type exit to quit, help for help.')
        except KeyboardInterrupt:
            pass
