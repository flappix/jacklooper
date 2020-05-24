import copy
import struct
from aubio import notes

class Loop:
	def __init__(self, _name, _jack_client, _sync_loop):
		self.name = str(_name)
		self.samples = []
		self.curr_sample = -1
		
		self.midi_tracks = []
		self.curr_midi_track = -1
		self.wav2midi_track = -1
		
		self.jack_client = _jack_client
		self.outport = self.jack_client.outports.register ( 'out' + str (self.name) )
		
		self.sync_loop = _sync_loop
		self.sync_samples = []
		self.state = 'empty' # empty, record, play
		self.isPlaying = False
		self.mute = False
			

	def setData (self, data, pos=None):
		if pos == None:
			self.samples.append ( copy.deepcopy (data) )
			self.curr_sample += 1
		else:
			self.samples[pos] = data;
	
	def getData (self, frames):
		if len(self.samples) > 0:
			return self.samples[self.curr_sample]
		
		return [0] * frames
	
	def getCurrMidiTrack (self):
		return self.midi_tracks[self.curr_midi_track]
	
	def getMidiData (self):
		return [cs for cs in self.midi_control_samples]
	
	def convertWav2Midi (self):
		o = notes('default', buf_size=256, hop_size=256, samplerate=44100)
		#o.set_threshold (0.7)
		o.set_silence (-30)
		
		self.addMidiTrack (wav2midi=True)
		for k in range(len(self.samples)):
			s = self.samples[k]
			new_note = o(s)
			if new_note[0] != 0:
				mt = self.getCurrMidiTrack()
				if len(mt.samples) == 0:
					mt.sync_sample = k
				
				mt.setDataFromAubio (new_note, k)
				
	def getWav2MidiTrack (self):
		if self.wav2midi_track != -1:
			return self.midi_tracks[self.wav2midi_track]
		
		return None
		
			
	
	def nextSample (self):
		if len(self.samples) > 0:
			self.curr_sample = (self.curr_sample + 1) % len (self.samples)
			return self.curr_sample < len(self.samples) - 1
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
		print ('add midi track %s' % self.getCurrMidiTrack().name)
	
	def deleteMidiTrack (self, track):
		try:
			print ('delete midi track %s' % self.midi_tracks[track].name)
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
	
	def deleteWav2MidiTrack (self):
		self.deleteMidiTrack (self.wav2midi_track)
	
	def selectNextMidiTrack (self):
		self.curr_midi_track = (self.curr_midi_track + 1) % len(self.midi_tracks)
		print ('select midi track %s' % self.getCurrMidiTrack().name)
	
	def selectPrevMidiTrack (self):
		if len(self.midi_tracks) > 0:
			self.curr_midi_track = (self.curr_midi_track - 1) % len(self.midi_tracks)
			print ('select midi track %s' % self.getCurrMidiTrack().name)
		else:
			self.curr_midi_track = -1
	
	def toggleMute (self):
		self.mute = not self.mute
	
	def log (self, msg):
		print ('loop ' + str(self.name) + ': ' + str(msg))

class MidiTrack:
	def __init__(self, _name, _loop, jack_client):
		self.name = str(_name)
		self.samples = {}
		self.curr_sample = -1
		self.sync_sample = -1
		self.loop = _loop
		self.enabled = False
		self.midi_outport = jack_client.midi_outports.register ( 'midi_out' + str (self.name) )
		self.isPlaying = False
	
	def setDataFromMidi (self, data, frame):
		b1, b2, b3 = struct.unpack('3B', data)
		
		self.samples[frame] = (b1, b2, b3)
		self.curr_sample = frame
	
	def setDataFromAubio (self, data, frame):
		self.samples[frame] = (144, data[0], 127)
		self.curr_sample = frame
	
	def nextSample (self):
		self.curr_sample = (self.curr_sample + 1) % len (self.loop.samples)
		return self.curr_sample < len(self.loop.samples) - 1
	
	def getData (self):
		if len(self.samples) > 0 and self.curr_sample in self.samples:
			return self.samples[self.curr_sample]
		
		return None
	
	def toggleEnable (self):
		self.enabled = not self.enabled
		print ('midi track %s: %s' % (self.name, 'enabled' if self.enabled else 'disabled'))
