
import thread
import os
import time

def exe(switch_ip, command):
	print("do script: %s %s" % (switch_ip, command))
	os.system("./config_script " + switch_ip + ' ' + command)
	print switch_ip + " done"

if __name__ == "__main__":

	f = open("tmplist")
	i = input("DHCP start address(ex: If it's 10.1.0.2 then enter 2): ")

	for line in f:
		thread.start_new_thread(exe, ('10.1.0.' + str(i), line))
		i = i + 1

	while 1:
		pass

	#print ip, name, location, password

