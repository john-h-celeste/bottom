# dashboard
# use a socket connection to send queries to the server and receive data back

import socket
import queue
import collections
import threading
import selectors
import time

clients = []

def drainqueue(q):
	items = []
	while True:
		try:
			items.append(q.get(False))
		except queue.Empty:
			break
	return items

def sendthread():
	while True:
		for client in clients:
			tosend = drainqueue(client.tosend)
			client._sends([message for tid,message in tosend])
			for tid,message in tosend:
				client.waiting.put(tid)

selector = selectors.DefaultSelector()

def recvthread():
	while len(clients) == 0:
		time.sleep(0.1) # wait for a connection to start
	while True:
		for key,mask in selector.select():
			client = key.data
			message = client._recv()
			tid = client.waiting.get()
			client.recieved[tid].put(message)

threading.Thread(target = sendthread).start()
threading.Thread(target = recvthread).start()

class Client:
	def __init__(self, s):
		self.s = s
		self.buffer = b''
		self.tosend = queue.Queue()
		self.waiting = queue.Queue()
		self.recieved = collections.defaultdict(queue.Queue)
		clients.append(self)
		selector.register(self.s, selectors.EVENT_READ, self)

	def _sends(self, commands):
		assert all(b'\n' not in command for command in commands)
		self.s.sendall(b''.join(bytes(command) + b'\n' for command in commands))


	def sends(self, commands):
		tid = threading.get_ident()
		for command in commands:
			self.tosend.put((tid, command))

	def send(self, command):
		self.sends([command])

	def _recv(self):
		while b'END ' not in self.buffer:
			self.buffer += self.s.recv(1024)
		data,rest = self.buffer.split(b'END ', 1)
		command,self.buffer = rest.split(b'\n', 1)
		return (command, data)

	def recv(self):
		tid = threading.get_ident()
		return self.recieved[tid].get()

	def runs(self, commands):
		self.sends(commands)
		out = []
		for command in commands:
			rcmd,data = self.recv()
			assert command == rcmd
			out.append(data)
		return out

	def run(self, command):
		return self.runs([command])[0]

def connect(host, port):
	if ':' in host:
		addr_type = socket.AF_INET6
	else:
		addr_type = socket.AF_INET
	s = socket.socket(addr_type, socket.SOCK_STREAM)
	s.connect((host, port))
	return Client(s)

def shutdown():
	for client in clients:
		client.tosend.shutdown()
		client.waiting.shutdown()
		for q in client.recieved.values():
			q.shutdown()