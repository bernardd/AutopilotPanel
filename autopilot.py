import logging
import serial
import time

from dataclasses import dataclass
from SimConnect import *
from typing import Callable

@dataclass
class Element:
	name: str
	id: str
	var: str # Value as read from the serial wire
	event: str
	read_modifier: Callable[[int], int] = lambda x: x
	update_modifier: Callable[[int], int] = lambda x: x
	val: int = None

elements = [
	Element('Heading', 'H', 'AUTOPILOT_HEADING_LOCK_DIR', 'HEADING_BUG_SET'),
	Element('Altitude', 'A', 'AUTOPILOT_ALTITUDE_LOCK_VAR', 'AP_ALT_VAR_SET_ENGLISH', lambda x: x/100, lambda x: x*100),
	Element('Speed', 'S', 'AUTOPILOT_AIRSPEED_HOLD_VAR', 'AP_SPD_VAR_SET'),
	Element('Vertical Speed', 'V', 'AUTOPILOT_VERTICAL_HOLD_VAR', 'AP_VS_VAR_SET_ENGLISH', lambda x: x/10, lambda x: x*10),
	# MS's baro, which is only displayed in INHg, is of course in units of 1/16th of a millibar in the API
	Element('QNH', 'Q', 'KOHLSMAN_SETTING_HG', 'KOHLSMAN_SET', lambda x: x*100, lambda x: round(((x / 100) * 33.864) * 16)),
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
		e.val = read_val(e.var, e.id, e.val, e.read_modifier)

def read_val(var, id, val, modifier):
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
			e.val = update_val(data, e.val, e.event, e.update_modifier)
			success = True
			break

	if not success:
		print(f'Unknown command: #{cmd}')

def update_val(data, val, event, modifier):
	new_val = int(data[1:])
	print(f'Updating #{event} from #{val} to #{new_val}')
	if (new_val != val):
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
