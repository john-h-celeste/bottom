import tkbuilder
import tkinter

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import collections
import time
import threading
import json
import re

import client

load = collections.deque()

#conn = client.connect('fd0f:e7d3:333e:4d00:a00:27ff:fe7d:e72', 8090)
conn = client.connect('192.168.1.156', 8090)
print(client.clients)

def getstats():
	data = conn.run(b'stats')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	cpudata = {}
	stats = {}
	for line in lines[:-1]:
		key,*parts = line.split(b' ')
		if key == b'cpu':
			parts = parts[1:]
		parts = [int(part) for part in parts]
		if re.match(b'cpu\\d+', key):
			cpudata[int(key[3:])] = parts
		else:
			stats[str(key, 'utf-8')] = parts
	cpustats = [cpudata[i] for i in range(len(cpudata))]
	stats['cpus'] = cpustats
	return stats

def getload():
	data = conn.run(b'load')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	avg1,avg5,avg15,schedulingentities,newestpid = lines[0].split(b' ')
	return float(avg1), float(avg5), float(avg15)

def getcpuinfo():
	data = conn.run(b'cpu')
	cpudatas = data.split(b'\n\n')
	assert cpudatas[-1] == b''
	cpus = []
	for i,cpudata in enumerate(cpudatas[:-1]):
		lines = cpudata.split(b'\n')
		cpu = {}
		for line in lines:
			print(line)
			key,value = line.split(b':', 1)
			key = key.rstrip(b'\t')
			value = value.lstrip(b' ')
			cpu[str(key, 'utf-8')] = str(value, 'utf-8')
		assert cpu['processor'] == str(i)
		del cpu['processor']
		cpus.append(cpu)
	return cpus

def getmeminfo():
	data = conn.run(b'meminfo')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	meminfo = {}
	for line in lines:
		key,value = line.split(b': ', 1)
		value = value.lstrip(b' ')
		match value.split(b' '):
			case [value, b'kB']:
				pass
			case [value]:
				pass
		meminfo[str(key, 'utf-8')] = int(value)
	return meminfo

def getdiskinfo():
	lsblkdata = json.loads(conn.run(b'lsblk'))
	diskstatsdata = conn.run(b'diskstats')
	lines = diskstatsdata.split(b'\n')
	assert lines[-1] == b''
	diskstats = {}
	for line in lines[:-1]:
		major,minor,name,*parts = line.split()
		parts = [int(major), int(minor)] + [int(part) for part in parts]
		diskstats[str(name, 'utf-8')] = parts
	print(repr(lsblkdata))
	print(repr(diskstats))

def loadcollector(plot):
	x = []
	y1 = []
	y2 = []
	y3 = []
	while running:
		load1,load5,load15 = getload()
		x.append(time.time())
		y1.append(load1)
		y2.append(load5)
		y3.append(load15)
		plot.clear()
		now = time.time()
		x2 = [now - t for t in x if now - t < 60]
		plot.plot(x2, y1[-len(x2):])
		plot.plot(x2, y2[-len(x2):])
		plot.plot(x2, y3[-len(x2):])
		plot.set_xlim(60, 0)
		plot.set_ylim(0, top = None)
		canvas.draw()
		time.sleep(1)

def getcpuusage():
	stats = getstats()
	cpus = stats['cpus']
	total = stats['cpu']
	usage = (total[0], total[1], total[2], total[3])
	usages = []
	for cpu in cpus:
		usages.append((cpu[0], cpu[1], cpu[2], cpu[3]))
	return [usage, *usages]

USER_HZ = 100
def usagecollector(plot):
	currusages = getcpuusage()
	x = []
	ys = [[] for _ in currusages]
	usages = collections.deque(maxlen = 5)
	for i in range(5):
		usages.append((time.time(), getcpuusage()))
		time.sleep(0.2)
	while running:
		usages.append((time.time(), getcpuusage()))
		prevtime,prevusages = usages[0]
		currtime,currusages = usages[-1]
		difference = [[c - p for p,c in zip(ps, cs)] for ps,cs in zip(prevusages, currusages)]
		dt = currtime - prevtime
		x.append(currtime)
		for y,d in zip(ys, difference):
			y.append(d[0] / dt / USER_HZ)
		plot.clear()
		now = time.time()
		x2 = [now - t for t in x if now - t < 10]
		for y in ys[1:]:
			plot.plot(x2, y[-len(x2):])
		plot.set_xlim(10, 0)
		plot.set_ylim(0, 1)
		canvas.draw()
		time.sleep(0.2)

class FigureBuilder(tkbuilder.TkBuilder):
	childrenargs = []

	def constructor(self, root, table, *args, figure, canvas_key = None, **kwargs):
		canvas = FigureCanvasTkAgg(figure, master = root)
		if canvas_key is not None:
			table[canvas_key] = canvas
		return canvas.get_tk_widget(), {}

fig = Figure(figsize = (10, 5), dpi = 100)
plot1 = fig.add_subplot(1, 2, 1)
plot2 = fig.add_subplot(1, 2, 2)

layout = tkbuilder.FrameBuilder(children = [
	FigureBuilder(figure = fig, canvas_key = 'canvas', geometry = tkbuilder.Pack(anchor = 'n'))
], geometry = tkbuilder.Pack())

root = tkinter.Tk()

parts = {}
layout.build(root, parts)
canvas = parts['canvas']

running = True
threading.Thread(target = loadcollector, args = (plot1,)).start()
threading.Thread(target = usagecollector, args = (plot2,)).start()
root.mainloop()
client.shutdown()
runnung = False