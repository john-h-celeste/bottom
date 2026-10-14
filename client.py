# dashboard
# use a socket connection to send queries to the server and receive data back

import socket

class Client:
	def __init__(self, s):
		self.s = s
		self.buffer = b''

	def sends(self, commands):
		assert all(b'\n' not in command for command in commands)
		self.s.sendall(b''.join(bytes(command) + b'\n' for command in commands))

	def send(self, command):
		self.sends([command])

	def recv(self):
		while b'END ' not in self.buffer:
			self.buffer += self.s.recv(1024)
		data,rest = self.buffer.split(b'END ', 1)
		command,self.buffer = rest.split(b'\n', 1)
		return (command, data)

	def runs(self, commands):
		self.sends(commands)
		out = []
		for command in commands:
			rcmd,data = self.recv()
			assert command == rcmd
			out.append(data)
		return out

	def run(self, command):
		return self.runs([command])

def connect(host, port):
	if ':' in host:
		addr_type = socket.AF_INET6
	else:
		addr_type = socket.AF_INET
	s = socket.socket(addr_type, socket.SOCK_STREAM)
	s.connect((host, port))
	return Client(s)

