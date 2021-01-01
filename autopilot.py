import logging
import math
import serial
import time

from dataclasses import dataclass
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

elements = [
	#		  Name					ID	  Variable								Event								set_from									read_modifier		update_modifier   set_from_modifier
	Element('Heading', 			'H', 'AUTOPILOT_HEADING_LOCK_DIR', 	'HEADING_BUG_SET',			'PLANE_HEADING_DEGREES_TRUE',    lambda x: x,		lambda x: x, 		lambda x: math.degrees(x)),
	Element('Altitude', 			'A', 'AUTOPILOT_ALTITUDE_LOCK_VAR', 'AP_ALT_VAR_SET_ENGLISH', 	'PLANE_ALTITUDE',						lambda x: x/100, 	lambda x: x*100,  lambda x: x/100),
	Element('Speed', 				'S', 'AUTOPILOT_AIRSPEED_HOLD_VAR', 'AP_SPD_VAR_SET',				'AIRSPEED_INDICATED'),
	Element('Vertical Speed', 	'V', 'AUTOPILOT_VERTICAL_HOLD_VAR', 'AP_VS_VAR_SET_ENGLISH', 	'', 										lambda x: x/10, 	lambda x: x*10),
	# MSFS's baro, which is only displayed in INHg, is of course in units of 1/16th of a millibar in the API. Because obviously.
	Element('QNH', 				'Q', 'KOHLSMAN_SETTING_HG', 			'KOHLSMAN_SET', 				'', 										lambda x: x*100, 	lambda x: round(((x / 100) * 33.864) * 16)),
]

# Setup
def connect_sim(sc):
	try:
		sc.connect()
	except ConnectionError:
		print('No running MSFS found. Retrying in 2 seconds')
		time.sleep(2)
		connect_sim(sc)

def connect_serial():
	ser.write(b'C')
	ser.flush()
	b = ser.read()
	if b != b'C':
		connect_serial()


# Incoming from sim
def read_state():
	for e in elements:
		e.val = read_from_sim_update_panel(e.var, e.id, e.val, e.read_modifier)

def read_from_sim_update_panel(var, id, val, modifier):
	new_val = ar.get(var)
	if new_val == None:
		return val

	new_val = round(modifier(new_val))
	if new_val != val:
		print(f'New #{var} of #{new_val} (old: #{val})')
		ser.write(f'#{id}#{new_val})\r\n'.encode())
	return new_val


# Incoming from AP Panel
def handle_data(data):
	print(f'Received #{data}')
	cmd = data[0]
	success = False
	for e in elements:
		if cmd == e.id:
			if data[1] == 'P':
				val = read_from_sim_update_panel(e.set_from, e.id, e.val, e.set_from_modifier)
			else:
				val = read_from_panel(data, e.val)
			e.val = update_sim_val(val, e.val, e.event, e.update_modifier)
			success = True
			break

	if not success:
		print(f'Unknown command: #{cmd}')

def read_from_panel(data, event):
	new_val = int(data[1:])
	return new_val

def update_sim_val(new_val, curr_val, event, modifier):
	print(f'Updating #{event} from #{curr_val} to #{new_val}')
	if (new_val != curr_val):
		sim_val = modifier(new_val)
		e = ae.find(event)
		e(sim_val)
	return new_val

# Main
ser = serial.Serial(port='COM3', baudrate=115200, timeout=0.2)

sc = SimConnect(auto_connect=False)
ar = AircraftRequests(sc)
ae = AircraftEvents(sc)

connect_sim(sc)
print("Connected to sim")

connect_serial()
print("Connected to serial port")

while 1:
	data = ser.readline().decode().strip()
	if (data != ''):
		handle_data(data)
	else:
		read_state()
