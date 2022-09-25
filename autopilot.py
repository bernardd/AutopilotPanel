# vim: set tabstop=3 noexpandtab shiftwidth=3 softtabstop=3 autoindent:
import logging
import math
import serial
import sys
import time

from dataclasses import dataclass
from gui import GUI
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QApplication
from SimConnect import *
from typing import Callable

@dataclass
class Element:
	name: str
	id: str
	var: str
	event: str
	set_from: str = ''
	read_modifier: Callable[[int], int] = lambda x: x
	update_modifier: Callable[[int], int] = lambda x: x
	set_from_modifier: Callable[[float], int] = lambda x: x
	val: int = None # Value as read from the serial wire

@dataclass
class Button:
	name: str
	id: str
	event: str

class AP(QObject):
	elements = [
			#		Name				ID		Variable						Event						set_from						read_modifier		update_modifier		set_from_modifier
			Element('Heading',			'H',	'AUTOPILOT_HEADING_LOCK_DIR',	'HEADING_BUG_SET',			'PLANE_HEADING_DEGREES_TRUE',	lambda x: x,		lambda x: x, 		lambda x: math.degrees(x)),
			Element('Altitude',			'A',	'AUTOPILOT_ALTITUDE_LOCK_VAR',	'AP_ALT_VAR_SET_ENGLISH',	'PLANE_ALTITUDE',				lambda x: x/100,	lambda x: x*100,	lambda x: x/100),
			Element('Speed',			'S',	'AUTOPILOT_AIRSPEED_HOLD_VAR',	'AP_SPD_VAR_SET',			'AIRSPEED_INDICATED'),
			Element('Vertical Speed',	'V',	'AUTOPILOT_VERTICAL_HOLD_VAR',	'AP_VS_VAR_SET_ENGLISH',	'',								lambda x: x/10,		lambda x: x*10),
			# MSFS's baro, which is only displayed in INHg, is of course in units of 1/16th of a millibar in the API. Because obviously.
			Element('QNH',				'Q',	'KOHLSMAN_SETTING_HG',			'KOHLSMAN_SET',				'',								lambda x: x*100,	lambda x: round(((x / 100) * 33.864) * 16)),
			]

	buttons = [
			Button('AP',  'A', 'AP_MASTER'),
			Button('FD',  'F', 'TOGGLE_FLIGHT_DIRECTOR'),
			Button('HDG', 'H', 'AP_PANEL_HEADING_HOLD'),
			Button('ALT', 'L', 'AP_PANEL_ALTITUDE_HOLD'),
			Button('NAV', 'N', 'AP_NAV1_HOLD'),
			Button('APR', 'P', 'AP_APR_HOLD'),
			Button('VNV', 'V', 'AP_VS_HOLD'), # TODO
			Button('VS',  'S', 'AP_VS_HOLD'),
			Button('FLC', 'C', 'FLIGHT_LEVEL_CHANGE'),
			Button('IAS', 'I', 'AP_PANEL_SPEED_HOLD')
			]

	def __init__(self, parent=None):
		super().__init__(parent)
		self.sim_connected = False
		self.device_connected = False

		self.timer = QTimer(self)
		self.timer.timeout.connect(self.main_loop)
		self.timer.start(0)

		self.ser = None
		self.sc = None

		self.gui = GUI()

	# Setup
	def connect_sim(self):
		try:
			if self.sc == None:
				self.sc = SimConnect()

			self.ar = AircraftRequests(self.sc)
			self.ae = AircraftEvents(self.sc)
			return True
		except ConnectionError:
			self.sc = None
			return False

	def connect_device(self):
		try:
			if self.ser == None:
				self.ser = serial.Serial(port='COM4', baudrate=115200, timeout=0.2)

			self.ser.write(b'C')
			self.ser.flush()
			b = self.ser.read()
			return b == b'C'
		except serial.SerialException:
			self.ser = None
			return False

	# Incoming from sim
	def read_state(self):
		for e in self.elements:
			e.val = self.read_from_sim_update_panel(e.var, e.id, e.val, e.read_modifier)

	def read_from_sim_update_panel(self, var, id, val, modifier):
		new_val = self.ar.get(var)
		if new_val == None:
			return val

		new_val = round(modifier(new_val))
		if new_val != val:
			self.gui.console_line(f'New {var} of {new_val} (old: {val})')
			self.ser.write(f'{id}{new_val})\r\n'.encode())

		return new_val

	# Incoming from AP Panel
	def handle_data(self, data):
		self.gui.console_line(f'Received {data}')
		cmd = data[0]
		success = False
		if cmd == 'B':
			success = self.handle_button(data[1])
		elif cmd == '#':
			success = True
		else:
			for e in self.elements:
				if cmd == e.id:
					if data[1] == 'P':
						val = self.read_from_sim_update_panel(e.set_from, e.id, e.val, e.set_from_modifier)
					else:
						val = self.read_from_panel(data, e.val)
					e.val = self.update_sim_val(val, e.val, e.event, e.update_modifier)
					success = True
					break

		if not success:
			self.gui.console_line(f'Unknown command: {cmd}')

	def handle_button(self, cmd):
		for b in self.buttons:
			if cmd == b.id:
				e = self.ae.find(b.event)
				e()
				return True
		return False

	def read_from_panel(self, data, event):
		new_val = int(data[1:])
		return new_val

	def update_sim_val(self, new_val, curr_val, event, modifier):
		self.gui.console_line(f'Updating {event} from {curr_val} to {new_val}')
		if (new_val != curr_val):
			sim_val = modifier(new_val)
			e = self.ae.find(event)
			e(sim_val)
		return new_val

	def main_loop(self):
		if not self.sim_connected:
			self.sim_connected = self.connect_sim()
			self.gui.set_sim_connected(self.sim_connected)

		if not self.device_connected:
			self.device_connected = self.connect_device()
			self.gui.set_device_connected(self.device_connected)

		if self.sim_connected and self.device_connected:
			try:
				data = self.ser.readline().decode().strip()
				if (data != ''):
					self.handle_data(data)
				else:
					self.read_state()
			except serial.SerialException:
				self.ser = None
				self.device_connected = False
			except OSError:
				self.sc = None
				self.sim_connected = False

# Main

app = QApplication(sys.argv)
ap = AP()
sys.exit(app.exec())
