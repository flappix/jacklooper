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
import collections
#import multiprocessing as mp

class Looper:
	
	def __init__(self, num_loops=8, buffer_size=300):
		self.jack_client = jack.Client('Looper')
		self.inport = self.jack_client.inports.register ('in')

		self.loops = [Loop ('0', self.jack_client, 'master')]
		self.curr_loop = self.loops[0]
		self.sync_loop = self.loops[0]
		
		self.addLoops (num_loops - 1)
		self.curr_loop = self.loops[0]
		
		self.buffer = collections.deque (maxlen=round ( (self.jack_client.samplerate / self.jack_client.blocksize) * (buffer_size / 1000) ) )
		
		self.midi_record = False

		self.record_treshhold = 0.05
		
		# default	- press -> recording -> press -> playing -> press -> recording -> ...
		# delete	- press -> recording -> press -> playing -> press -> delete    -> press -> recording -> press -> playing -> ...
		# pause		- press -> recording -> press -> playing -> press -> plause    -> press -> playing -> ...
		self.record_mode = 'default'
		self.record_counter = 0

		self.syncManager = SyncManager()

		self.midi_inport = self.jack_client.midi_inports.register ('midi_capture')
	
	def addLoop (self):
		self.midi_record = False
		self.curr_loop = Loop ( str (len(self.loops)), self.jack_client, self.sync_loop )
		self.loops.append (self.curr_loop)
	
	def addLoops (self, n):
		for i in range(n):
			self.addLoop()
	
	def deleteCurrLoop (self):
		print ('delete loop %s' % self.curr_loop.name)
		self.midi_record = False
		self.curr_loop.state = 'empty'
		i = self.loops.index (self.curr_loop)
		self.loops[i].outport.unregister()
		del self.loops[i]
		self.selectPrevLoop()
	
	def setCurrLoop (self, i):
		if i >= 0 and i < len(self.loops):
			self.midi_record = False
			
			if self.curr_loop != self.loops[i]:
				self.record_counter = 0
			
			self.curr_loop = self.loops[i]
			print ('set curr_loop to ' + self.curr_loop.name)
		else:
			print ('no such loop')
	
	def selectNextLoop (self):
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i + 1) % len(self.loops)
		self.curr_loop = self.loops[i]
		self.record_counter = 0
		print ('set curr_loop to ' + self.curr_loop.name)
		
	def selectPrevLoop (self):
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i - 1) % len(self.loops)
		self.curr_loop = self.loops[i]
		self.record_counter = 0
		print ('set curr_loop to ' + self.curr_loop.name)
	
	def toggleRecord (self):
		if self.record_counter == 0 or ( self.record_mode == 'delete' and self.record_counter == 2 ):
			self.curr_loop.clear (self)
			
		elif self.record_counter == 1:
			self.curr_loop.log ('stop recording')
			
			if self.curr_loop != self.sync_loop:
				
				if self.curr_loop.getSyncMode() == 'continous':
					self.syncManager.calc_sync_samples (self.sync_loop, self.curr_loop)
			else: # self.curr_loop == self.sync_loop
				if len (self.curr_loop.samples) > 0:
					if self.curr_loop.getSyncMode() == 'continous':
						for l in self.loops:
							if l != self.curr_loop  and l.state != 'empty':
								self.syncManager.calc_sync_samples (self.sync_loop, l)
					
									
							l.sync_samples = []
							break
			
			self.curr_loop.stopRecord()
			
			
			
			## after executing the midi track has wrong names
			#p = mp.Process(target=self.curr_loop.convertWav2Midi)
			#p.start()
			#
			#self.curr_loop.convertWav2Midi()
	
		
		elif self.record_mode == 'pause':
			if self.record_counter % 2 == 0:
				curr_loop.log ('pause')
				self.curr_loop.state = 'wait'
				self.curr_loop.curr_sample = []
			elif self.record_counter % 2 == 1:
				curr_loop.log ('playing')
				self.curr_loop.state = 'play'
		
		if self.record_counter == 0:
			print ('waiting for treshold')
		
		if self.record_mode == 'default':
			self.record_counter = (self.record_counter + 1) %  2
		elif self.record_mode == 'delete':
			self.record_counter = (self.record_counter + 1) %  3
		elif self.record_mode == 'pause':
			self.record_counter += 1
		
			
	
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
	
	def getSlaveLoops (self):
		return [l for l in self.loops if l != self.sync_loop]
	
	def setRecordMode (self, mode):
		self.record_mode = mode
		self.record_counter = 0
			

argParser = argparse.ArgumentParser()
argParser.add_argument('-l', '--loops', default=8, metavar='N', type=int, help='create N initial loops, default=8')	
argParser.add_argument('-i', '--input', help='toggle record on stdin input', action='store_true')	
argParser.add_argument('-b', '--buffer', help='buffer size in milliseconds', type=int,  default=300, metavar='N')	
argParser.add_argument('-t', '--threshold', help='audio signal threshold at which recording starts after sending the record command', type=float,  default=0.05, metavar='N')	
args = argParser.parse_args()

looper = Looper (args.loops, args.buffer)
looper.record_treshhold = args.threshold
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
	b = looper.inport.get_array()
	curr_loop = looper.curr_loop
	if looper.record_counter == 1:
		if curr_loop.state != 'record' and max(b) > looper.record_treshhold:
			curr_loop.state = 'record'
			
			curr_loop.head_buffer = list (looper.buffer)
			
			if curr_loop != looper.sync_loop and len (curr_loop.sync_loop.curr_sample) > 0:
				# sync_samples should be empty list here
				# TODO: test this line:
				#curr_loop.sync_samples = [curr_loop.sync_loop.curr_sample]
				curr_loop.sync_samples.append (curr_loop.sync_loop.curr_sample[0])
			else:
				for l in looper.getSlaveLoops():
					if len (l.curr_sample) > 0:
						l.sync_samples = [l.sync_loop.curr_sample[0]]
						
			curr_loop.log ('recording')
		
		if curr_loop.state == 'record':
			curr_loop.setData (b)
	
		
	looper.buffer.append (b) # ring buffer
	
	# record midi
	if looper.midi_record:
		
		any_input = False
		for offset, data in looper.midi_inport.incoming_midi_events():
			any_input = True
			b1, b2, b3 = struct.unpack('3B', data)
			if len(data) == 3:
				curr_loop.getCurrMidiTrack().setDataFromMidi (data)
				
				if curr_loop.getCurrMidiTrack().sync_sample == -1:
					curr_loop.getCurrMidiTrack().sync_sample = curr_loop.curr_sample[0]
		
		if not any_input and curr_loop.getCurrMidiTrack().sync_sample != -1:
			curr_loop.getCurrMidiTrack().copyLastSample()
		
	for loop in looper.loops:
		
		# wav play
		playNullSample = True
		if loop.state == 'play':
			
			# append tail_buffer if needed
			if len (loop.tail_buffer) < len (looper.buffer):
				loop.tail_buffer.append (b)
				if len (loop.tail_buffer) >= len (looper.buffer):
					loop.samples = loop.samples + loop.tail_buffer
					loop.log ('samples after add tail_buffer: %s' % len(loop.samples) )
			
			if loop == looper.sync_loop:
				if len (loop.curr_sample) == 0:
					loop.addPlayInstance()
					# for first play after record start loop from record start without playing the head_buffer
					loop.curr_sample[0] = len (loop.head_buffer)
				elif len (loop.curr_sample) == 1 and loop.curr_sample[0] >= len (loop.samples) - len (loop.tail_buffer) - len (loop.head_buffer):
					loop.addPlayInstance()
				
			#if loop != looper.sync_loop and \
			#   loop.isPlaying and \
			#   len (loop.curr_sample) == 1 and len (loop.samples) - loop.curr_sample[0] <= len (loop.samples) / 10 and \
			#   loop.sync_loop.curr_sample[0] in loop.sync_samples:
			#	loop.addPlayInstance()
			
			add = False
			if loop != looper.sync_loop:
				for cs in looper.sync_loop.curr_sample:
					if cs in loop.sync_samples:
						print ('sample in sync_samples')
						loop.addPlayInstance()
						add = True
						break
			
			# add play instance right after recording without wait for the next cycle to start
			if not add:
				if loop != looper.sync_loop and len (loop.curr_sample) == 0:
					for ss in reversed (loop.sync_samples):
						for cs in looper.sync_loop.curr_sample:
							if cs > ss:
								loop.addPlayInstance()
								loop.curr_sample[0] = cs - ss
								print (1)
								
								break
			
			#print (looper.sync_loop)
			#print (looper.sync_loop.curr_sample)
			#print (len(loop.sync_samples))
			if loop == looper.sync_loop or \
				len (loop.curr_sample) > 0 or \
			   ( len (looper.sync_loop.curr_sample) > 0 and \
			    looper.sync_loop.curr_sample[0] in loop.sync_samples ):
				
				#for cs in loop.curr_sample:
				#	print ('loop ' + loop.name + ' curr sample: ' + str(cs))
					
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
					if loop.curr_sample[0] >= mt.sync_sample and loop.curr_sample[0] - mt.sync_sample < len(mt.samples):	
						mt.curr_sample = loop.curr_sample[0] - mt.sync_sample
						play = True
					elif loop.curr_sample[0] < mt.sync_sample and (len (loop.samples) - mt.sync_sample) + loop.curr_sample[0] < len(mt.samples):
						play = True
						mt.curr_sample = (len (loop.samples) - mt.sync_sample) + loop.curr_sample[0]
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
			
			# test
			#t1 = Loop ('master t1', looper.jack_client, 'master')
			#t2 = Loop ('slave t2', looper.jack_client, t1)
			#
			#t1.samples = [0] * 1020
			#t1.head_buffer = [0] * 10
			#t1.tail_buffer = [0] * 10
			#
			#t2.samples = [0] * 250
			#t2.head_buffer = [0] * 10
			#t2.sync_samples = [0]
			#looper.syncManager.calc_sync_samples (t1, t2)
			#t2.stopRecord()
			
			if args.input:
				input()
				looper.toggleRecord()
			
				time.sleep (0.1);
			else:
				time.sleep (1000)
