#!/usr/bin/env python3

import jack
import random
import numpy as np
from loop import Loop
from SyncManager import SyncManager
from MidiInterface import MidiInterface
import struct
import argparse
import time
import multiprocessing as mp
class Looper:
	
	def __init__(self, num_loops=8):
		self.jack_client = jack.Client('Looper')
		self.inport = self.jack_client.inports.register ('in')

		self.loops = [Loop ('0', self.jack_client, 'master')]
		self.curr_loop = self.loops[0]
		self.sync_loop = self.loops[0]
		
		self.addLoops (num_loops - 1)
		self.curr_loop = self.loops[0]
		
		self.record = False
		self.midi_record = False

		self.record_treshhold = 0.05

		self.syncManager = SyncManager()

		self.midi_inport = self.jack_client.midi_inports.register ('midi_capture')
	
	def addLoop (self):
		self.record = False
		self.midi_record = False
		self.curr_loop = Loop ( str (len(self.loops)), self.jack_client, self.sync_loop )
		self.loops.append (self.curr_loop)
	
	def addLoops (self, n):
		for i in range(n):
			self.addLoop()
	
	def deleteCurrLoop (self):
		print ('delete loop %s' % self.curr_loop.name)
		self.record = False
		self.midi_record = False
		self.curr_loop.state = 'empty'
		i = self.loops.index (self.curr_loop)
		self.loops[i].outport.unregister()
		del self.loops[i]
		self.selectPrevLoop()
	
	def setCurrLoop (self, i):
		if i >= 0 and i < len(self.loops):
			self.record = False
			self.midi_record = False
			self.curr_loop = self.loops[i]
			print ('set curr_loop to ' + self.curr_loop.name)
		else:
			print ('no such loop')
	
	def selectNextLoop (self):
		self.record = False
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i + 1) % len(self.loops)
		self.curr_loop = self.loops[i]
		print ('set curr_loop to ' + self.curr_loop.name)
		
	def selectPrevLoop (self):
		self.record = False
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i - 1) % len(self.loops)
		self.curr_loop = self.loops[i]
		print ('set curr_loop to ' + self.curr_loop.name)
	
	def toggleRecord (self):
		if self.record == False:
			print ('waiting for threshold')
			self.curr_loop.state = 'empty'
			self.curr_loop.samples = []
			self.curr_loop.sync_samples = []
			self.curr_loop.curr_sample = -1
			self.curr_loop.deleteAllMidiTracks()
		
		if self.record:
			print ('stop recording')
			print ( len(self.curr_loop.samples) )
			if self.curr_loop != self.sync_loop:
				
				if self.curr_loop.getSyncMode() == 'continous':
					self.syncManager.calc_sync_samples (self.sync_loop, self.curr_loop)
					print (self.curr_loop.sync_samples)
			
			## after executing the midi track has wrong names
			#p = mp.Process(target=self.curr_loop.convertWav2Midi)
			#p.start()
			self.curr_loop.state = 'play'
			#
			#self.curr_loop.convertWav2Midi()
		
		self.record = not self.record
	
	def toggleRecordMidi (self):
		midi_track = self.curr_loop.getCurrMidiTrack()
		
		if midi_track != None:
			if not self.midi_record:
				print ('start midi record')
				self.curr_loop.getCurrMidiTrack().isPlaying = False
				self.curr_loop.getCurrMidiTrack().enabled = False
				self.curr_loop.getCurrMidiTrack().samples = []
				self.curr_loop.getCurrMidiTrack().sync_sample = -1
			else:
				print ('end midi record')
				self.curr_loop.getCurrMidiTrack().enabled = True
				
			self.midi_record = not self.midi_record
			

argParser = argparse.ArgumentParser()
argParser.add_argument('-l', '--loops', default=8, metavar='N', type=int, help='create N initial loops, default=8')	
argParser.add_argument('-i', '--input', help='toggle record on stdin input', action='store_true')	
args = argParser.parse_args()

looper = Looper (args.loops)
midiInterface = MidiInterface (looper)

@looper.jack_client.set_process_callback
def process (frames):
	global looper
	global fst
	global exe
	
	null_sample = [0] * frames
	
	# record midi commands
	for offset, data in midiInterface.midi_inport.incoming_midi_events():
		b1, b2, b3 = struct.unpack('3B', data)
		
		#if b3 == 127:
		midiInterface.executeMidiCmd (b2, b3)
		
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
		
		any_input = False
		for offset, data in looper.midi_inport.incoming_midi_events():
			any_input = True
			b1, b2, b3 = struct.unpack('3B', data)
			if len(data) == 3:
				curr_loop.getCurrMidiTrack().setDataFromMidi (data)
				
				if curr_loop.getCurrMidiTrack().sync_sample == -1:
					curr_loop.getCurrMidiTrack().sync_sample = curr_loop.curr_sample
		
		if not any_input and curr_loop.getCurrMidiTrack().sync_sample != -1:
			curr_loop.getCurrMidiTrack().copyLastSample()
		
	# play
	
	for loop in looper.loops:
		
		# wav play
		playNullSample = True
		if loop.state == 'play':
			if loop == looper.sync_loop or loop.isPlaying or loop.sync_loop.curr_sample in loop.sync_samples:
					
				loop.isPlaying = loop.nextSample()
				
				if not loop.mute:
					loop.outport.get_array()[:] = loop.getData (frames)
					playNullSample = False
					
		if playNullSample:
			loop.outport.get_array()[:] = null_sample
		
		# midi play
		for mt in loop.midi_tracks:
			mt.midi_outport.clear_buffer()
			
			#print (mt.sync_sample)
			#print (loop.curr_sample)
			#print (len(loop.samples))
			#print (len(mt.samples))
			#print (mt.enabled)
			
			
			#if mt.enabled and (mt.isPlaying or mt.sync_sample == loop.curr_sample):
			if mt.enabled:
				play = True
				### TODO: handle midi tracks which are longer than wav loop
				if not mt.isPlaying:
					if loop.curr_sample >= mt.sync_sample and loop.curr_sample - mt.sync_sample < len(mt.samples):	
						mt.curr_sample = loop.curr_sample - mt.sync_sample
						play = True
					elif loop.curr_sample < mt.sync_sample and (len (loop.samples) - mt.sync_sample) + loop.curr_sample < len(mt.samples):
						play = True
						mt.curr_sample = (len (loop.samples) - mt.sync_sample) + loop.curr_sample
					else:
						play = False
						#print ('not play')
				
				if play:
					#print ('play midi')
					mt.isPlaying = mt.nextSample()
					data = mt.getData()
					if data != None:
						#print ('write midi')
						mt.midi_outport.write_midi_event (0, data)

if __name__ == '__main__':
	
	with looper.jack_client:
		looper.jack_client.activate()
		while True:
			
			if args.input:
				input()
				looper.toggleRecord()
			
				time.sleep (0.1);
			else:
				time.sleep (1000)
