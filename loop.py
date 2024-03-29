import struct
#from aubio import notes
import numpy as np
from MidiInterface import MidiInterface
from midi_map import midi_map
import time

class Loop:
	def __init__(self, _name, _jack_client, _looper):
		self.name = str(_name)
		self.samples = []
		self.temp_samples = [] # recording go to this and will be copies to samples after recording
		self.curr_sample = []
		self.head_buffer = []
		self.temp_head_buffer = []
		self.tail_buffer = []
		
		self.volume = 1
		self.fade_volume = []
		
		self.midi_tracks = []
		self.curr_midi_track = -1
		self.wav2midi_track = -1
		
		self.jack_client = _jack_client
		self.outport = self.jack_client.outports.register ( 'out' + str (self.name) )
		
		self.looper = _looper
		self.sync_samples = []
		self.temp_sync_samples = []
		self.state = 'empty' # empty, wait, record, play
		self.isPlaying = False
		self.mute = False
		self.stopping = False
		
		self.grounded = True # send one null-Sample after clear to ground and avoid strange noises
		
		self.sync_modes = ['continous', 'gap']
		self.curr_sync_mode = 0

	def setData (self, data, pos=None):
		if pos == None:
			self.temp_samples.append (data)
		else:
			self.temp_samples[pos] = data
	
	def getData (self, frames):
		if self.stopping:
			if len(self.fade_volume) == 0:
				self.curr_sample = []
				self.state = 'wait'
				self.grounded = False
				self.stopping = False
				print(1)
				return [0] * frames
				
		if len(self.samples) > 0:
			volume = self.volume
			# fade out when loop is stopped (paused)
			if len(self.fade_volume) > 0:
				volume = self.fade_volume[0]
				self.fade_volume.pop (0)

			return sum ([np.multiply (self.samples[s], volume) for s in self.curr_sample])
		
		return [0] * frames
	
	def applyRecord (self):
		self.clear()
		
		self.samples = self.temp_samples
		self.temp_samples = []
		
		self.sync_samples = self.temp_sync_samples
		self.temp_sync_samples = []
		
		self.head_buffer = self.temp_head_buffer
		self.temp_head_buffer = []
	
	def stopRecord (self):
		self.curr_sample = []
		
		if len (self.samples) > 0:
			self.log ('head_buffer: %s' % len(self.head_buffer))
			self.log ('samples before buffer merge: %s' % len(self.samples))
			
			# fade in head_buffer
			self.head_buffer = [self.head_buffer[i] * m for i, m in enumerate ( np.linspace ( 0, 1, num=len (self.head_buffer) ) )]
				
			self.samples = self.head_buffer + self.samples
			self.log ('samples after add head_buffer: %s' % len(self.samples))
			
			if not self.looper.isMaster (self):
				if len (self.looper.sync_loop.samples) == 0:
					print ('ERROR sync_loop.samples is empty')
					print ('self.name: ' + self.name)
					print ('self.looper.sync_loop.name: ' + self.looper.sync_loop.name)
				
				# bug: 2nd repeat cycle within one master loop starts too early
				self.sync_samples = sorted ([( s - len (self.head_buffer) ) % len (self.looper.sync_loop.samples) for s in self.sync_samples])
				#self.sync_samples = [( s - ( len (self.head_buffer) * (1 if i == 0 else 0) ) ) % len (self.looper.sync_loop.samples) for i, s in enumerate (self.sync_samples)]
				
				self.log ('sync_samples after add head_buffer: %s' % self.sync_samples)
			else:
				self.sync_samples = []
			
			self.state = 'play'
		
		else:
			self.state = 'empty'
	
	def dropRecording (self):
		self.temp_samples = []
		self.temp_sync_samples = []
		
		if len (self.samples) > 0:
			self.state = 'play'
		else:
			self.state = 'empty'
		
	
	def addPlayInstance (self, start=-1):
		self.curr_sample += [start]
		
		self.log ('add play instance at')
		if not self.looper.isMaster (self):
			for i, cs in enumerate (self.looper.sync_loop.curr_sample):
				self.looper.sync_loop.log ('curr_sample[%s]: %s' % (i, cs))
		for i, cs in enumerate (self.curr_sample):
			self.log ('curr_sample[%s]: %s' % (i, cs))
	
	def stop (self):
		self.log ('pause')
		# not working
		#self.stopping = True
		#self.fade_volume = list ( np.linspace (1, 0, 5) )
		
		self.state = 'wait'
		self.curr_sample = []
		self.grounded = False
	
	def getCurrMidiTrack (self):
		if self.curr_midi_track != -1:
			return self.midi_tracks[self.curr_midi_track]
		
		return None
	
	def getTailBuffer (self):
		if len (self.tail_buffer) < self.looper.buffer.maxlen:
			return self.tail_buffer + ([0] * self.looper.buffer.maxlen)
	
	def getMidiData (self):
		return [cs for cs in self.midi_control_samples]
	
	#def convertWav2Midi (self):
	#	o = notes('default', buf_size=self.jack_client.blocksize, hop_size=self.jack_client.blocksize, samplerate=self.jack_client.samplerate)
	#	o.set_silence (-30)
	#	
	#	self.addMidiTrack (wav2midi=True)
	#	for k in range(len(self.samples)):
	#		s = self.samples[k]
	#		new_note = o(s)
	#		if new_note[0] != 0:
	#			mt = self.getCurrMidiTrack()
	#			if len(mt.samples) == 0:
	#				mt.sync_sample = k
	#			
	#			#mt.setDataFromAubio (new_note, k)
	#			time.sleep (0.1)
				
	def getWav2MidiTrack (self):
		if self.wav2midi_track != -1:
			return self.midi_tracks[self.wav2midi_track]
		
		return None
		
			
	
	def nextSample (self):
		if len(self.samples) > 0:
			self.curr_sample[:] = [i + 1 for i in self.curr_sample if i + 1 < len (self.samples) - 1 ]
			return True
			
		else:
			return False
	
	def addMidiTrack (self, wav2midi=False):
		if wav2midi:
			# delete old wav2midi track if there is any
			if self.wav2midi_track != -1:
				self.midi_tracks[self.wav2midi_track].midi_outport.unregister()
				del self.midi_tracks[self.wav2midi_track]
					
		name = self.name + '_' + str ( len (self.midi_tracks) ) if not wav2midi else self.name + '_wav2midi'
		self.midi_tracks.append ( MidiTrack (name, self, self.jack_client ) )
		
		if wav2midi:
			self.wav2midi_track = len(self.midi_tracks) - 1
			
		self.curr_midi_track = len(self.midi_tracks) - 1
		self.log ('add midi track %s' % self.getCurrMidiTrack().name)
	
	def deleteMidiTrack (self, track):
		try:
			self.log ('delete midi track %s' % self.midi_tracks[track].name)
			self.midi_tracks[track].midi_outport.unregister()
			
			if track == self.wav2midi_track:
				self.wav2midi_track = -1
			
			self.midi_tracks[track].enabled = False
			del self.midi_tracks[track]
			
			if track == self.curr_midi_track:
				self.selectPrevMidiTrack()
		except IndexError:
			print ('no track %s' % track)
		
	def deleteCurrMidiTrack (self):
		self.deleteMidiTrack (self.curr_midi_track)
		self.curr_midi_track = len(self.midi_tracks) - 1
	
	def deleteAllMidiTracks (self):
		for i in range ( len(self.midi_tracks) ):
			self.deleteMidiTrack (i)
	
	def deleteWav2MidiTrack (self):
		self.deleteMidiTrack (self.wav2midi_track)
	
	def selectNextMidiTrack (self):
		if len(self.midi_tracks) > 0:
			self.curr_midi_track = (self.curr_midi_track + 1) % len(self.midi_tracks)
			self.log ('select midi track %s' % self.getCurrMidiTrack().name)
		else:
			self.curr_midi_track = -1
			
	def selectPrevMidiTrack (self):
		if len(self.midi_tracks) > 0:
			self.curr_midi_track = (self.curr_midi_track - 1) % len(self.midi_tracks)
			self.log ('select midi track %s' % self.getCurrMidiTrack().name)
		else:
			self.curr_midi_track = -1
	
	def toggleMute (self):
		self.mute = not self.mute
	
	def setSyncMode (self, mode):
		if mode in ['gap', 'contonius']:
			self.sync_mode = mode
		else:
			self.log ('invalid sync mode %s' % str(mode))
	
	def toggleSyncMode (self):
		self.curr_sync_mode = (self.curr_sync_mode + 1) % len(self.sync_modes)
	
	def getSyncMode (self):
		return self.sync_modes[self.curr_sync_mode]
	
	def setVolume (self, volume):
		# logarithmic: n^4 / 140000000 maps from 0 to ~1.85
		v = MidiInterface.linearTrans (0, 2, 0, 127, volume) 
		if v >= 0 and v <= 1:
			self.volume = v
		
	
	def clear (self):
		self.log ('cleared')
		self.state = 'empty'
		self.samples = []
		#self.temp_samples = []
		self.head_buffer = []
		self.tail_buffer = []
		self.sync_samples = []
		self.curr_sample = []
		self.deleteAllMidiTracks()
		self.grounded = False
	
		if self.looper.isMaster (self):
			# turn first non-empty loop into master looper
			for l in self.looper.loops:
				if len (l.samples) > 0:
					self.looper.set_sync_loop (l)
					break
		
	
	def log (self, msg):
		if self.looper.debug:
			print ('loop ' + str(self.name) + (' (master) ' if self.looper.isMaster (self) else '') + ': ' + str(msg))

class MidiTrack:
	def __init__(self, _name, _loop, jack_client):
		self.name = str(_name)
		self.samples = {}
		self.loop = _loop
		self.enabled = False
		self.midi_outport = jack_client.midi_outports.register ( 'midi_out' + str (self.name) )
		self.isPlaying = False
		
		self.midi_record_cmd = list ( midi_map.keys() )[list ( midi_map.values() ).index ('toggle_record_midi')]
	
	def setDataFromMidi (self, data, sync_sample):
		b1, b2, b3 = struct.unpack('3B', data)
		if b2 != self.midi_record_cmd:
			self.samples[sync_sample] = (b1, b2, b3)
	
	#def setDataFromAubio (self, data, frame):
	#	self.samples[frame] = (144, data[0], 127)
	#	self.curr_sample = frame
		
	
	def getData (self, sync_sample):
		if sync_sample in self.samples:
			return self.samples[sync_sample]
		
		return None
	
	def toggleEnable (self):
		self.enabled = not self.enabled
		self.loop.log ('midi track %s: %s' % (self.name, 'enabled' if self.enabled else 'disabled'))
