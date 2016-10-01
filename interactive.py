from cmd import Cmd
import getpass
import cli

class Prompt(Cmd):
    def do_hello(self, args):
        """Says hello. If you provide a name, it will greet you with it."""
        if len(args) == 0:
            name = 'stranger'
        else:
            name = args
        print("Hello, %s" % name)

    def do_exit(self, args):
        """Exit the program."""
        raise SystemExit

    def do_EOF(self, args):
        """Exit the program."""
        raise SystemExit

    def do_http(self, args):
        """
        http - Connect a switch through HTTP protocal
        --
        http username@hostname
        --
        """
        host = "192.168.1.1"
        password = getpass.getpass('Password: ')
        cli.connect(host)
        if not cli.login("admin", password):
            return
        prompt.prompt = '(%s)> ' % host
        cli.logout()
        cli.close()

host = ""
prompt = Prompt()
prompt.prompt = '(not connect)> '
prompt.cmdloop('HP 1820 wrapper version 1.0')
