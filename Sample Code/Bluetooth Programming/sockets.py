################################# INTRODUCTION TO SOCKETS

# import socket

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #SOCK_STREAM allows for TCP Connection

# server = 'pythonprogramming.net'
# port = 80

# server_ip = socket.gethostbyname(server)
# print(server_ip)

# request = "GET / HTTP/1.1\nHost: "+server+"\n\n"
# s.connect((server,port,))
# s.send(request.encode())
# result = s.recv(4096) # Integer is the buffer for download

# #print(result)

# while (len(result) > 0):
# 	print(result)
# 	result = s.recv(4096)


################################# SOCKET SIMPLE PORT SCANNER

# import socket

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #SOCK_STREAM allows for TCP Connection

# print(s)

# server = 'pythonprogramming.net'

# def pscan(port):
# 	try:
# 		print('trying port ', port)
# 		s.connect((server, port))
# 		return True
# 	except:
# 		return False

# for x in range(79,81):
# 	if pscan(x):
# 		print("port",x,'is open')
# 	else:
# 		print("port",x,'is closed')

################################## THREADED PORT SCANNER

# import socket
# import threading
# from queue import Queue

# print_lock = threading.Lock()

# target = 'pythonprogramming.net'

# def portscan(port):
# 	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 	try:
# 		con = s.connect((target,port))
# 		with print_lock:
# 			print('port',port,'is open')

# 		con.close()

# 	except:
# 		pass

# def threader():
# 	while True:
# 		worker = q.get()
# 		portscan(worker)
# 		q.task_done()

# q = Queue()
# for x in range (100):
# 	t = threading.Thread(target=threader)
# 	t.daemon = True
# 	t.start()

# for worker in range(1,10000):
# 	q.put(worker)

# q.join()

################################## Socket Binding and Listening


# import socket
# import sys

# host = ''
# port = 5555
# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# try:
# 	s.bind((host,port))
# except socket.error as e:
# 	print(str(e))

# s.listen(5) #Parameter: how many incoming conections will fit in a queue before rejecting new conections

# conn, addr = s.accept()

# print('connected to: '+addr[0]+':'+str(addr[1]))


################################## Sockets: client server system


import socket
import sys
from _thread import * 

host = ''
port = 5555
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
	s.bind((host,port))
except socket.error as e:
	print(str(e))

s.listen(5) #Parameter: how many incoming conections will fit in a queue before rejecting new conections
print("waiting for a connection")
def threaded_client(conn):
	conn.send(str.encode('Welcome, type your info\n'))

	while True:
		data = conn.recv(2048)
		reply = 'Server output:' + data.decode('utf-8')
		if not data:
			break
		conn.sendall(str.encode(reply))
	conn.close()

while True:
	conn, addr = s.accept()
	print('connected to: '+addr[0]+':'+str(addr[1]))
	start_new_thread(threaded_client, (conn,))














