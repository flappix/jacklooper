import copy
import struct

class Loop:
	def __init__(self, _name, jack_client, _sync_loop):
		self.name = _name
		self.samples = []
		self.midi_samples = {}
		self.midi_control_samples = []
		self.curr_midi_control = -1
		self.curr_sample = -1
		self.outport = jack_client.outports.register ( 'out' + str (self.name) )
		self.midi_outport = jack_client.midi_outports.register ( 'notes_out' + str (self.name) )
		self.midi_control_outport = jack_client.midi_outports.register ( 'control_out' + str (self.name) )
		self.sync_loop = _sync_loop
		self.sync_samples = []
		self.state = 'empty' # empty, record, play
		self.isPlaying = False
		self.playMidi = False
		self.playMidiControl = False;
			

	def setData (self, data, pos=None):
		if pos == None:
			self.samples.append ( copy.deepcopy (data) )
			self.curr_sample += 1
		else:
			self.samples[pos] = data;
	
	def getData (self, frames):
		if self.samples != None:
			return self.samples[self.curr_sample]
		
		return [0] * frames
	
	def setMidiData (self, data, frame):
		b1, b2, b3 = struct.unpack('3B', data)
		self.midi_control_samples[self.curr_midi_control][frame] = (b1, b2, b3)
			
	
	def nextSample (self):
		self.curr_sample = (self.curr_sample + 1) % len (self.samples)
		return self.curr_sample == 0
	
	def addMidiControlSample (self):
		self.midi_control_samples.append ({})
		self.curr_midi_control_samples = len (self.midi_control_samples) - 1
			
	def getCurrMidiControlSample (self):
		return self.midi_control_samples[self.curr_midi_control]
		
	def log (self, msg):
		print ('loop ' + str(self.name) + ': ' + str(msg))
