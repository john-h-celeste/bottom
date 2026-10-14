# define a tkinter gui in a tree like structure and build it in one step
# written by Robert Vail on Aug 25, 2026

import tkinter as tk

class Geometry:
	pass

class Grid(Geometry):
	def __init__(self, **kwargs):
		self.kwargs = kwargs

	def manage(self, element):
		element.grid(**self.kwargs)

class Pack(Geometry):
	def __init__(self, **kwargs):
		self.kwargs = kwargs

	def manage(self, element):
		element.pack(**self.kwargs)

class TkBuilder:
	def __init__(self, *args, geometry = None, key = None, **kwargs):
		self.args = args
		self.kwargs = kwargs
		self.geometry = geometry
		self.key = key
		self.children = {}
		self.children_keys = {}
		for carg in self.childrenargs:
			self.children[carg] = kwargs.pop(carg, [])
			self.children_keys[carg] = kwargs.pop(carg + '_key', None)

	def build(self, root, table):
		thisroot,childrenroots = self.constructor(root, table, *self.args, **self.kwargs)
		if self.geometry is not None:
			self.geometry.manage(thisroot)
		children_tables = {}
		if table is not None:
			if self.key is not None:
				table[self.key] = thisroot
			for carg in self.childrenargs:
				if self.children_keys[carg] is not None:
					if self.children_keys[carg] not in table:
						table[self.children_keys[carg]] = {}
					children_tables[carg] = table[self.children_keys[carg]]
				else:
					children_tables[carg] = table
		else:
			for carg in self.childrenargs:
				children_tables[carg] = None
		for carg in self.childrenargs:
			for child in self.children[carg]:
				if callable(child):
					child(childrenroots[carg], children_tables[carg])
				else:
					child.build(childrenroots[carg], children_tables[carg])
		return thisroot

class TkBuilderLeaf(TkBuilder):
	childrenargs = []

	def constructor(self, root, table, *args, **kwargs):
		return self.element(root, *args, **kwargs), {}

class TkBuilderNode(TkBuilder):
	childrenargs = ['children']

	def constructor(self, root, table, *args, **kwargs):
		e = self.element(root, *args, **kwargs)
		return e, {'children': e}

class LabelBuilder(TkBuilderLeaf):
	element = tk.Label

class ButtonBuilder(TkBuilderLeaf):
	element = tk.Button

class TextBuilder(TkBuilderLeaf):
	element = tk.Text

class CanvasBuilder(TkBuilderLeaf):
	element = tk.Canvas

class FrameBuilder(TkBuilderNode):
	element = tk.Frame

class OptionMenuBuilder(TkBuilderLeaf):
	@staticmethod
	def element(root, *args, command, **kwargs):
		menu = tk.OptionMenu(root, *args, command = command)
		menu.config(**kwargs)
		return menu

class ScaleBuilder(TkBuilderLeaf):
	@staticmethod
	def element(root, *args, value, **kwargs):
		scale = tk.Scale(root, *args, **kwargs)
		scale.set(value)
		return scale
