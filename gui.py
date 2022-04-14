# vim: set tabstop=3 noexpandtab shiftwidth=3 softtabstop=3 autoindent:

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QPalette, QFont
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QTextEdit

class GUI():
	def __init__(self):
		self.w = QWidget()
		self.w.resize(600, 600)
		self.w.move(300, 300)
		
		self.sim_connected = Light()
		self.device_connected = Light()

		sim_label = QLabel('Connected to sim')
		device_label = QLabel('Connected to AP')

		sim_status = QHBoxLayout()
		sim_status.addWidget(self.sim_connected)
		sim_status.addWidget(sim_label)
		sim_status.addStretch()

		device_status = QHBoxLayout()
		device_status.addWidget(self.device_connected)
		device_status.addWidget(device_label)
		device_status.addStretch()

		palette = QPalette()
		palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.black)
		palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
		#font = QFont()
		#font.setStyleHint(QFont.StyleHint.TypeWriter)
		self.console = QTextEdit()
		self.console.setFontFamily('Courier')
		self.console.setPalette(palette)
		self.console.setReadOnly(True)
		self.console.setAutoFillBackground(True)

		vbox = QVBoxLayout()
		vbox.addLayout(sim_status)
		vbox.addLayout(device_status)
		vbox.addWidget(self.console)

		self.w.setLayout(vbox)
		self.w.setWindowTitle('AutoPilot')
		self.w.show()

	def set_sim_connected(self, state):
		self.sim_connected.set_state(state)

	def set_device_connected(self, state):
		self.device_connected.set_state(state)

	def console_line(self, line):
		self.console.append(line)


class Light(QWidget):
	def __init__(self):
		super().__init__()
		self.setFixedSize(30, 30)
		self.set_state(False)

	def set_state(self, state):
		if state:
			self.colour = Qt.GlobalColor.green
		else:
			self.colour = Qt.GlobalColor.red

		self.update()

	def paintEvent(self, event):
		width = 30
		height = 30
		painter = QPainter()
		painter.begin(self)
		painter.setRenderHint(QPainter.RenderHint.Antialiasing)
		painter.setBrush(self.colour)
		painter.drawEllipse(0, 0, width, height)
		painter.end()
