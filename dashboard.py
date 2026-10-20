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

def loadgraph(plot):
	try:
		data = []
		while running:
			now = time.time()
			load1,load5,load15 = getload()
			entry = {'time': now, 'l1': load1, 'l5': load5, 'l15': load15}

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			lockcanvas()
			plot.clear()
			plot.set_xlim(60, 0)
			#plot.set_ylim(0, top = None)
			plot.plot(timeseries, series('l1'))
			plot.plot(timeseries, series('l5'))
			plot.plot(timeseries, series('l15'))
			unlockcanvas()
			time.sleep(5)
	except client.ShutDown:
		pass

def getcpuusage():
	stats = getstats()
	cpus = stats['cpus']
	total = stats['cpu']
	usages = []
	for cpu in [total, *cpus]:
		usages.append((cpu[0], cpu[1], cpu[2], cpu[3], *cpu[3:]))
	return usages

USER_HZ = 100
def cpugraph(plot, detailplot):
	try:
		data = []
		currusages = getcpuusage()
		cpucount = len(currusages) - 1

		# set up total cpu graph
		totalcpu, = plot.plot([], [], label = 'Total CPU usage')
		plot.set_xlim(10, 0)
		plot.set_ylim(0, 4.2)
		plot.legend()

		cpulines = [detailplot.plot([], [], label = f'CPU {i + 1} usage')[0] for i in range(cpucount)]
		detailplot.set_xlim(10, 0)
		detailplot.set_ylim(0, 1.1)
		detailplot.legend()

		# initialize sliding window of cpu usages
		usages = collections.deque(maxlen = 5)
		for i in range(5):
			usages.append((time.time(), getcpuusage()))
			time.sleep(0.2)

		while running:
			now = time.time()
			usages.append((now, getcpuusage()))
			prevtime,prevusages = usages[0]
			currtime,currusages = usages[-1]
			difference = [[c - p for p,c in zip(ps, cs)] for ps,cs in zip(prevusages, currusages)]
			dt = currtime - prevtime
			entry = {'time': currtime}
			for i,d in enumerate(difference):
				for j,dd in enumerate(d):
					entry[(i, j)] = dd / dt / USER_HZ
				entry[(i, 'usage')] = (4 if i == 0 else 1) - (d[3] / dt / USER_HZ)

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			lockcanvas()
			for i in range(cpucount):
				cpulines[i].set_xdata(timeseries)
				cpulines[i].set_ydata(series((i + 1, 'usage')))
			totalcpu.set_xdata(timeseries)
			totalcpu.set_ydata(series((0, 'usage')))
			unlockcanvas()
			time.sleep(0.2)
	except client.ShutDown:
		pass

canvaslocks = {name: threading.Lock() for name in ['main', 'cpu']}

def lockcanvas(name = 'main'):
	canvaslocks[name].acquire()

def unlockcanvas(name = 'main'):
	canvaslocks[name].release()

def updatecanvas():
	while running:
		lockcanvas()
		canvas.draw()
		unlockcanvas()
		lockcanvas('cpu')
		canvas2.draw()
		unlockcanvas('cpu')

class FigureBuilder(tkbuilder.TkBuilder):
	childrenargs = []

	def constructor(self, root, table, *args, figure, canvas_key = None, **kwargs):
		canvas = FigureCanvasTkAgg(figure, master = root)
		if canvas_key is not None:
			table[canvas_key] = canvas
		return canvas.get_tk_widget(), {}

fig = Figure(figsize = (8, 1.5), dpi = 100, layout = 'constrained')
loadplot = fig.add_subplot(1, 4, 1)
cpuplot = fig.add_subplot(1, 4, 2)
plot3 = fig.add_subplot(1, 4, 3)
plot4 = fig.add_subplot(1, 4, 4)

cpufig = Figure(figsize = (8, 6), dpi = 100, layout = 'constrained')
cpudetail = cpufig.add_subplot(1, 1, 1)

layout = tkbuilder.FrameBuilder(children = [
	FigureBuilder(figure = fig, canvas_key = 'canvas', geometry = tkbuilder.Pack(anchor = 'n')),
	FigureBuilder(figure = cpufig, canvas_key = 'canvas2', geometry = tkbuilder.Pack(anchor = 'n')),
], geometry = tkbuilder.Pack())

root = tkinter.Tk()

parts = {}
layout.build(root, parts)
canvas = parts['canvas']
canvas2 = parts['canvas2']

running = True
threading.Thread(target = loadgraph, args = (loadplot,)).start()
threading.Thread(target = cpugraph, args = (cpuplot, cpudetail)).start()
threading.Thread(target = updatecanvas).start()
root.mainloop()
client.shutdown()
running = False