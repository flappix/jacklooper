#!/usr/bin/env python3

import jack
import random
import numpy
from loop import Loop
from SyncManager import SyncManager
from MidiInterface import MidiInterface
import struct

class Looper:
	
	def __init__(self):
		self.jack_client = jack.Client('Looper')
		self.inport = self.jack_client.inports.register ('in')

		self.loops = [Loop ('0', self.jack_client, 'master')]
		self.curr_loop = self.loops[0]
		self.sync_loop = self.loops[0]
		
		self.addLoops (7)
		self.curr_loop = self.loops[0]
		
		self.record = False
		self.playback = False
		self.midi_record = False

		self.record_treshhold = 0.05

		self.syncManager = SyncManager()

		self.midi_inport = self.jack_client.midi_inports.register ('midi_capture')
	
	def addLoop (self):
		self.curr_loop = Loop ( str (len(self.loops)), self.jack_client, self.sync_loop )
		self.loops.append (self.curr_loop)
	
	def addLoops (self, n):
		for i in range(n):
			self.addLoop()
	
	def setCurrLoop (self, _curr_loop):
		print ('set curr_loop to ' + _curr_loop.name)
		self.curr_loop = _curr_loop
	
	def toggleRecord (self):
		if self.record == False:
			print ('waiting for threshold')
			self.curr_loop.state = 'empty'
			self.curr_loop.samples = []
			if 0 in self.curr_loop.midi_tracks:
				self.curr_loop.midi_tracks[0].samples = []
		
		if self.record:
			print ('stop recording')
			if self.curr_loop != self.sync_loop:
				self.syncManager.calc_sync_samples (self.sync_loop, self.curr_loop)
			
			self.curr_loop.convertWav2Midi()
			self.curr_loop.state = 'play'
		
		self.record = not self.record
	
	def recordNewMidiTrack (self):
		if not self.midi_record:
			print ('start midi record')
			self.curr_loop.addMidiTrack()
		else:
			print ('end midi record')
			self.curr_loop.getCurrMidiTrack().setEnabled (True)
		self.midi_record = not self.midi_record
			
	
looper = Looper()
midiInterface = MidiInterface (looper)

@looper.jack_client.set_process_callback
def process (frames):
	global looper
	
	null_sample = [0] * frames
	
	# record midi commands
	for offset, data in midiInterface.midi_inport.incoming_midi_events():
		b1, b2, b3 = struct.unpack('3B', data)
		
		if b3 == 127:
			midiInterface.executeMidiCmd (b2)
		
	# record wav
	curr_loop = looper.curr_loop
	if looper.record:
		b = looper.inport.get_array()
		if curr_loop.state != 'record' and max(b) > looper.record_treshhold:
			curr_loop.state = 'record'
			if curr_loop.sync_loop != 'master':
				# sync_samples should be empty list here
				curr_loop.sync_samples.append ( curr_loop.sync_loop.curr_sample )
			print ('recording loop ' + curr_loop.name)
		
		if curr_loop.state == 'record':
			curr_loop.setData (b)
	
	# record midi
	if looper.midi_record:
		for offset, data in looper.midi_inport.incoming_midi_events():
			b1, b2, b3 = struct.unpack('3B', data)
			if len(data) == 3:
				curr_loop.getCurrMidiTrack().setDataFromMidi (data, curr_loop.curr_sample)
				curr_loop.getCurrMidiTrack().sync_sample = curr_loop.curr_sample
		
	# play
	
	for loop in looper.loops:
		
		# wav play
		if loop.state == 'play':
			if loop == looper.sync_loop or loop.isPlaying or loop.sync_loop.curr_sample in loop.sync_samples:
				
				loop.isPlaying = loop.nextSample()
				loop.outport.get_array()[:] = loop.getData (frames)
			else:
				loop.outport.get_array()[:] = null_sample
		else:
			loop.outport.get_array()[:] = null_sample
		
		# midi play
		for mt in loop.midi_tracks:
			mt.midi_outport.clear_buffer()

			if mt.enabled and (mt.isPlaying or mt.sync_sample == loop.curr_sample):
				mt.isPlaying = mt.nextSample()
				data = mt.getData()
				if data != None:
					mt.midi_outport.write_midi_event (0, data)
		

		
with looper.jack_client:
	looper.jack_client.activate()
	input()
	#i = 1
	#while True:
	#	input()
	#	print ('wait for treshold ' + looper.curr_loop.name);
	#	looper.record = True
	#	input()
	#	print ('finished recording')
	#	looper.record = False
	#	looper.curr_loop.state = 'transition'
	#	
	#	# calculate sync samples
	#	if i > 1:
	#		looper.syncManager.calc_sync_samples (looper.sync_loop, looper.curr_loop)
	#	
	#	looper.curr_loop.convertWav2Midi()
	#	looper.curr_loop.getCurrMidiTrack().enabled = True
	#	looper.curr_loop.state = 'play'
	#	
	#	looper.curr_loop.addMidiTrack()
	#	print ('press enter to start midi control record')
	#	input()
	#	looper.midi_record = True
	#	print ('press enter to exit midi control record')
	#	input()
	#	looper.midi_record = False
	#	looper.curr_loop.getCurrMidiTrack().enabled = True
	#	
	#	looper.addLoop()
	#	
	#	i += 1
