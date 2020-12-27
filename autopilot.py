import logging
import serial
import time

from SimConnect import *

# Values as read from the wire
heading = None
altitude = None
speed = None
vspeed = None
qnh = None




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
		print(b)
		connect_serial()


def read_state():
	read_heading()
	read_altitude()
	read_speed()
	read_vspeed()
	read_qnh()

def read_heading():
	global heading
	heading = read_val('AUTOPILOT_HEADING_LOCK_DIR', 'H', heading)

def read_altitude():
	global altitude
	altitude = read_val('AUTOPILOT_ALTITUDE_LOCK_VAR', 'A', altitude, lambda x: x / 100)

def read_speed():
	global speed
	speed = read_val('AUTOPILOT_AIRSPEED_HOLD_VAR', 'S', speed)

def read_vspeed():
	global vspeed
	vspeed = read_val('AUTOPILOT_VERTICAL_HOLD_VAR', 'V', vspeed, lambda x: x / 10)

def read_qnh():
	global qnh
	qnh = read_val('KOHLSMAN_SETTING_HG', 'Q', qnh, lambda x: x * 100)

def read_val(var, id, val, modifier = lambda x: x):
	new_val = ar.get(var)
	if new_val == None:
		return val

	new_val = round(modifier(new_val))
	if new_val != val:
		print(f'New #{var} of #{new_val} (old: #{val})')
		ser.write(f'#{id}#{new_val})\r\n'.encode())
	return new_val

def update_heading(data):
	global heading
	heading = update_val(data, heading, 'HEADING_BUG_SET')

def update_altitude(data):
	global altitude
	altitude = update_val(data, altitude, 'AP_ALT_VAR_SET_ENGLISH', lambda x: x * 100)

def update_speed(data):
	global speed
	speed = update_val(data, speed, 'AP_SPD_VAR_SET')

def update_vspeed(data):
	global vspeed
	vspeed = update_val(data, vspeed, 'AP_VS_VAR_SET_ENGLISH', lambda x: x * 10)

def update_qnh(data):
	global qnh
	# MS's baro, which is only displayed in INHg, is of course in units of 1/16th of a millibar in the API
	modifier = lambda x: round(((x / 100) * 33.864) * 16)
	qnh = update_val(data, speed, 'KOHLSMAN_SET', modifier)

def update_val(data, val, event, modifier = lambda x: x):
	new_val = int(data[1:])
	print(f'Updating #{event} from #{val} to #{new_val}')
	if (new_val != val):
		sim_val = modifier(new_val)
		print(f'sim_val: #{sim_val}')
		e = ae.find(event)
		e(sim_val)
	return new_val


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
		print(f'Received #{data}')
		cmd = data[0]
		if cmd == 'H': update_heading(data)
		elif cmd == 'A': update_altitude(data)
		elif cmd == 'S': update_speed(data)
		elif cmd == 'V': update_vspeed(data)
		elif cmd == 'Q': update_qnh(data)
		else: print(f'Unknown command: #{cmd}')

	else:
		read_state()
