import tkbuilder
import tkinter
import client

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg, 
NavigationToolbar2Tk)

import collections
import time
import threading

load = collections.deque()

conn = client.connect('fd0f:e7d3:333e:4d00:a00:27ff:fe7d:e72', 8090)

def loadcollector():
	while True:
		loaddata = conn.run(b'load')
		print(float(str(loaddata.split(b' ')[0], 'utf-8')))
		time.sleep(0.5)

threading.Thread(target = loadcollector).start()

def plot():
    fig = Figure(figsize = (5, 5), dpi = 100)
    y = [i**2 for i in range(101)]
    plot1 = fig.add_subplot(111)
    plot1.plot(y)
    canvas = FigureCanvasTkAgg(fig, master = graphcontainer)  
    canvas.draw()
    canvas.draw()
    canvas.get_tk_widget().pack()

layout = tkbuilder.FrameBuilder(children = [
	tkbuilder.ButtonBuilder(command = plot, height = 2, width = 10, text = 'Plot', geometry = tkbuilder.Pack(anchor = 'n')),
	tkbuilder.FrameBuilder(children = [], key = 'graphcontainer', geometry = tkbuilder.Pack(anchor = 'n')),
], geometry = tkbuilder.Pack())

root = tkinter.Tk()

parts = {}
layout.build(root, parts)
graphcontainer = parts['graphcontainer']
root.mainloop()