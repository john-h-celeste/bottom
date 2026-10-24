import tkbuilder
import tkinter

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import collections
import time
import threading
import json
import re
import os

import client

def getstats(conn):
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

def getload(conn):
	data = conn.run(b'load')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	avg1,avg5,avg15,schedulingentities,newestpid = lines[0].split(b' ')
	return float(avg1), float(avg5), float(avg15)

def getcpuinfo(conn):
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

def getmeminfo(conn):
	data = conn.run(b'meminfo')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	meminfo = {}
	for line in lines[:-1]:
		key,value = line.split(b': ', 1)
		value = value.lstrip(b' ')
		match value.split(b' '):
			case [value, b'kB']:
				pass
			case [value]:
				pass
		meminfo[str(key, 'utf-8')] = int(value)
	return meminfo

def getdiskinfo(conn):
	diskstatsdata = conn.run(b'diskstats')
	lines = diskstatsdata.split(b'\n')
	assert lines[-1] == b''
	diskstats = {}
	for line in lines[:-1]:
		major,minor,name,*parts = line.split()
		parts = [str(name, 'utf-8')] + [int(part) for part in parts]
		diskstats[f'{int(major)}:{int(minor)}'] = parts
	return diskstats

def getlsblk(conn):
	lsblkdata = json.loads(conn.run(b'lsblk'))
	devs = {dev['kname']:dev for dev in lsblkdata}
	roots = [] # the devices that are not partitions of others
	for dev in lsblkdata:
		dev['children'] = []
	for dev in lsblkdata:
		if dev['pkname'] is not None:
			parent = devs[dev['pkname']]
			parent['children'].append(dev)
		else:
			parent = None
			roots.append(dev)
		dev['parent'] = parent
	return roots, devs

def getnetinfo(conn):
	data = conn.run(b'netstat')
	lines = data.split(b'\n')
	assert lines[-1] == b''
	for line in lines[:-1]:
		if line.startswith(b'    InOctets: '):
			netin = int(line.split()[1])
		if line.startswith(b'    OutOctets: '):
			netout = int(line.split()[1])
	return netin, netout

def loadgraph(context, plot):
	conn = context['conn']
	try:
		data = []
		while context['running']:
			now = time.time()
			load1,load5,load15 = getload(conn)
			entry = {'time': now, 'l1': load1, 'l5': load5, 'l15': load15}

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			with context['canvaslocks']['main']:
				plot.clear()
				plot.set_title('Load')
				plot.set_xlim(60, 0)
				#plot.set_ylim(0, top = None)
				plot.plot(timeseries, series('l1'))
				plot.plot(timeseries, series('l5'))
				plot.plot(timeseries, series('l15'))
			time.sleep(5)
	except client.ShutDown:
		pass

def getcpuusage(conn):
	stats = getstats(conn)
	cpus = stats['cpus']
	total = stats['cpu']
	usages = []
	for cpu in [total, *cpus]:
		usages.append((cpu[0], cpu[1], cpu[2], cpu[3], *cpu[3:]))
	return usages

USER_HZ = 100
def cpugraph(context, plot, detailplot):
	conn = context['conn']
	try:
		data = []
		currusages = getcpuusage(conn)
		cpucount = len(currusages) - 1

		# set up total cpu graph
		totalcpu, = plot.plot([], [], label = 'Total CPU usage')
		plot.set_xlim(10, 0)
		plot.set_ylim(0, cpucount + 0.2)
		plot.set_title('CPU')

		cpulines = [detailplot.plot([], [], label = f'CPU {i + 1} usage')[0] for i in range(cpucount)]
		detailplot.set_xlim(10, 0)
		detailplot.set_ylim(0, 1.1)
		detailplot.legend()

		# initialize sliding window of cpu usages
		usages = collections.deque(maxlen = 5)
		for i in range(5):
			usages.append((time.time(), getcpuusage(conn)))
			time.sleep(0.2)

		while context['running']:
			now = time.time()
			usages.append((now, getcpuusage(conn)))
			prevtime,prevusages = usages[0]
			currtime,currusages = usages[-1]
			difference = [[c - p for p,c in zip(ps, cs)] for ps,cs in zip(prevusages, currusages)]
			dt = currtime - prevtime
			entry = {'time': currtime}
			for i,d in enumerate(difference):
				for j,dd in enumerate(d):
					entry[(i, j)] = dd / dt / USER_HZ
				entry[(i, 'usage')] = max((cpucount if i == 0 else 1) - (d[3] / dt / USER_HZ), 0)

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			with context['canvaslocks']['cpu']:
				for i in range(cpucount):
					cpulines[i].set_xdata(timeseries)
					cpulines[i].set_ydata(series((i + 1, 'usage')))
			with context['canvaslocks']['main']:
				totalcpu.set_xdata(timeseries)
				totalcpu.set_ydata(series((0, 'usage')))
			time.sleep(0.2)
	except client.ShutDown:
		pass

def memgraph(context, plot, memplot, swapplot):
	conn = context['conn']
	try:
		meminfo = getmeminfo(conn)
		data = []
		while context['running']:
			now = time.time()
			meminfo = getmeminfo(conn)
			entry = {'time': now, 'memused': meminfo['MemTotal'] - meminfo['MemFree'], 'swapused+': meminfo['MemTotal'] - meminfo['MemFree'] + meminfo['SwapTotal'] - meminfo['SwapFree'], 'swapused': meminfo['SwapTotal'] - meminfo['SwapFree']}

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			with context['canvaslocks']['main']:
				plot.cla()
				plot.set_title('Memory')
				plot.set_xlim(10, 0)
				plot.set_ylim(0, meminfo['MemTotal'] + meminfo['SwapTotal'])
				plot.plot(timeseries, series('swapused+'))
				plot.fill_between(timeseries, series('swapused+'), series('memused'), alpha = 0.2)
				plot.plot(timeseries, series('memused'))
				plot.fill_between(timeseries, series('memused'), alpha = 0.2)
			with context['canvaslocks']['mem']:
				memplot.cla()
				memplot.set_title('Memory Used')
				memplot.set_xlim(10, 0)
				memplot.set_ylim(0, max(1, meminfo['MemTotal']))
				memplot.plot(timeseries, series('memused'))
				swapplot.cla()
				swapplot.set_title('Swap Used')
				swapplot.set_xlim(10, 0)
				swapplot.set_ylim(0, max(1, meminfo['SwapTotal']))
				swapplot.plot(timeseries, series('swapused'))
			time.sleep(0.1)
	except client.ShutDown:
		pass

def netgraph(context, plot):
	conn = context['conn']
	try:
		data = []

		# initialize sliding window of network usage
		netstats = collections.deque(maxlen = 5)
		for i in range(5):
			netstats.append((time.time(), getnetinfo(conn)))
			time.sleep(0.2)

		while context['running']:
			now = time.time()
			netstats.append((now, getnetinfo(conn)))
			prevtime,prevnetstats = netstats[0]
			currtime,currnetstats = netstats[-1]
			difference = [c - p for p,c in zip(prevnetstats, currnetstats)]
			dt = currtime - prevtime
			entry = {'time': currtime, 'in': difference[0], 'out': difference[1]}

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			with context['canvaslocks']['main']:
				plot.cla()
				plot.set_xlim(10, 0)
				plot.set_title('Network')
				plot.plot(timeseries, series('in'))
				plot.plot(timeseries, series('out'))
			time.sleep(0.2)
	except client.ShutDown:
		pass

def diskgraph(context, plot):
	conn = context['conn']
	try:
		data = []

		def getdiskusage(conn):
			diskinfos = [getdiskinfo(conn)[dev['maj:min']] for dev in getlsblk(conn)[0]]
			readtotal = sum(disk[2] for disk in diskinfos)
			writetotal = sum(disk[6] for disk in diskinfos)
			return readtotal, writetotal

		# initialize sliding window of network usage
		diskstats = collections.deque(maxlen = 5)
		for i in range(5):
			diskstats.append((time.time(), getdiskusage(conn)))
			time.sleep(0.2)

		while context['running']:
			now = time.time()
			diskstats.append((now, getdiskusage(conn)))
			prevtime,prevdiskstats = diskstats[0]
			currtime,currdiskstats = diskstats[-1]
			difference = [c - p for p,c in zip(prevdiskstats, currdiskstats)]
			dt = currtime - prevtime
			entry = {'time': currtime, 'read': difference[0], 'write': difference[1]}

			data.append(entry)
			data = [x for x in data if now - x['time'] < 60]
			series = lambda k: [x[k] for x in data]
			timeseries = [now - t for t in series('time')]

			with context['canvaslocks']['main']:
				plot.cla()
				plot.set_xlim(10, 0)
				plot.set_title('Disk')
				plot.plot(timeseries, series('read'))
				plot.plot(timeseries, series('write'))
			time.sleep(0.2)
	except client.ShutDown:
		pass

def updatecanvas(context):
	while context['running']:
		for active in [*context['activecanvases']]:
			with context['canvaslocks'][active]:
				context['canvases'][active].draw()

class FigureBuilder(tkbuilder.TkBuilder):
	childrenargs = []

	def constructor(self, root, table, *args, figure, canvas_key = None, **kwargs):
		canvas = FigureCanvasTkAgg(figure, master = root)
		if canvas_key is not None:
			table[canvas_key] = canvas
		return canvas.get_tk_widget(), {}

def createwindow(ip):
	print(ip)
	conn = client.connect(ip, 9375)

	fig = Figure(figsize = (8, 1.5), dpi = 100, layout = 'constrained')
	loadplot = fig.add_subplot(1, 5, 1)
	cpuplot = fig.add_subplot(1, 5, 2)
	memplot = fig.add_subplot(1, 5, 3)
	netplot = fig.add_subplot(1, 5, 4)
	diskplot = fig.add_subplot(1, 5, 5)

	cpufig = Figure(figsize = (8, 6), dpi = 100, layout = 'constrained')
	cpudetail = cpufig.add_subplot(1, 1, 1)

	memfig = Figure(figsize = (8, 6), dpi = 100, layout = 'constrained')
	memdetail = memfig.add_subplot(1, 2, 1)
	swapdetail = memfig.add_subplot(1, 2, 2)

	def setcpugraph():
		parts['cpugraph'].grid_remove()
		parts['memgraph'].grid_remove()

		parts['cpugraph'].grid()
		context['activecanvases'].add('cpu')

	def setmemgraph():
		parts['cpugraph'].grid_remove()
		parts['memgraph'].grid_remove()

		parts['memgraph'].grid()
		context['activecanvases'].add('mem')

	layout = tkbuilder.FrameBuilder(children = [
		tkbuilder.LabelBuilder(text = ip, geometry = tkbuilder.Grid(row = 0, column = 1, columnspan = 2)),
		FigureBuilder(figure = fig, canvas_key = 'canvas', geometry = tkbuilder.Grid(row = 1, column = 1, columnspan = 2)),
		tkbuilder.ButtonBuilder(text = 'CPU', command = setcpugraph, geometry = tkbuilder.Grid(row = 2, column = 1)),
		tkbuilder.ButtonBuilder(text = 'Memory', command = setmemgraph, geometry = tkbuilder.Grid(row = 2, column = 2)),
		tkbuilder.FrameBuilder(key = 'cpugraph', children = [
			FigureBuilder(figure = cpufig, canvas_key = 'cpucanvas', geometry = tkbuilder.Pack(anchor = 'n')),
		], geometry = tkbuilder.Grid(row = 3, column = 1, columnspan = 2)),
		tkbuilder.FrameBuilder(key = 'memgraph', children = [
			FigureBuilder(figure = memfig, canvas_key = 'memcanvas', geometry = tkbuilder.Pack(anchor = 'n')),
		], geometry = tkbuilder.Grid(row = 3, column = 1, columnspan = 2)),
	], geometry = tkbuilder.Pack())

	root = tkinter.Toplevel()
	root.title(ip)

	parts = {}
	layout.build(root, parts)

	context = {'running': True, 'conn': conn}

	context['canvaslocks'] = {name: threading.Lock() for name in ['main', 'cpu', 'mem']}

	context['canvases'] = {}
	context['activecanvases'] = {'main'}

	context['canvases']['main'] = parts['canvas']
	context['canvases']['cpu'] = parts['cpucanvas']
	context['canvases']['mem'] = parts['memcanvas']

	setcpugraph()

	threading.Thread(target = loadgraph, args = (context, loadplot)).start()
	threading.Thread(target = cpugraph, args = (context, cpuplot, cpudetail)).start()
	threading.Thread(target = memgraph, args = (context, memplot, memdetail, swapdetail)).start()
	threading.Thread(target = netgraph, args = (context, netplot)).start()
	threading.Thread(target = diskgraph, args = (context, diskplot)).start()
	threading.Thread(target = updatecanvas, args = (context,)).start()

	def on_closing():
		context['running'] = False
		conn.close()
		root.destroy()
	root.protocol("WM_DELETE_WINDOW", on_closing)

	root.mainloop()

def main():
	layout = tkbuilder.FrameBuilder(children = [
		tkbuilder.LabelBuilder(text = 'IP: ', geometry = tkbuilder.Grid(row = 0, column = 0)),
		tkbuilder.TextBuilder(height = 1, width = 40, key = 'ip', geometry = tkbuilder.Grid(row = 0, column = 1)),
		tkbuilder.ButtonBuilder(text = 'Open Dashboard', command = lambda: createwindow(ipinput.get('1.0', tkinter.END).strip()), geometry = tkbuilder.Grid(row = 1, column = 1)),
		tkbuilder.ButtonBuilder(text = 'Open Dashboard 1', command = lambda: createwindow('34.68.184.128'), geometry = tkbuilder.Grid(row = 2, column = 1)),
		tkbuilder.ButtonBuilder(text = 'Open Dashboard 2', command = lambda: createwindow('fd0f:e7d3:333e:4d00:a00:27ff:fe7d:e72'), geometry = tkbuilder.Grid(row = 33, column = 1)),
	], geometry = tkbuilder.Pack())

	root = tkinter.Tk()

	parts = {}
	layout.build(root, parts)
	ipinput = parts['ip']
	root.mainloop()


	#createwindow('34.68.184.128')
	#createwindow('fd0f:e7d3:333e:4d00:a00:27ff:fe7d:e72')
	client.shutdown()

	time.sleep(0.5)
	os._exit(0)

if __name__ == '__main__':
	main()