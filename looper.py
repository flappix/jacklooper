#!/usr/bin/env python3

import jack
import random
import numpy as np
import copy
from loop import Loop
from SyncManager import SyncManager
from MidiInterface import MidiInterface
import struct
import argparse
import time
import collections
#import multiprocessing as mp

from utils import dist_ring

class Looper:
	
	def __init__(self, num_loops=8, buffer_size=300, deviation=0.6):
		self.jack_client = jack.Client('Looper')
		print (self.jack_client.blocksize)
		self.inport = self.jack_client.inports.register ('in')

		self.loops = [Loop ('0', self.jack_client, self)]
		self.curr_loop = self.loops[0]
		self.sync_loop = self.loops[0]
		
		self.addLoops (num_loops - 1)
		self.curr_loop = self.loops[0]
		
		self.buffer = collections.deque (maxlen=round ( (self.jack_client.samplerate / self.jack_client.blocksize) * (buffer_size / 1000) ) )
		
		self.midi_record = False

		self.record_treshhold = 0.05
		self.deviation_samples = self.time2samples (deviation)
		
		# default	- press -> recording -> press -> playing -> press -> recording -> ...
		# delete	- press -> recording -> press -> playing -> press -> delete    -> press -> recording -> press -> playing -> ...
		# pause		- press -> recording -> press -> playing -> press -> plause    -> press -> playing -> ...
		self.record_mode = 'default'
		self.record_counter = 0

		self.syncManager = SyncManager()

		self.midi_inport = self.jack_client.midi_inports.register ('midi_capture')
		
		self.debug = False
	
	def samples2time (self, n_samples : int):
		return n_samples // self.jack_client.samplerate
		
	def time2samples (self, seconds):
		return seconds * ( self.jack_client.samplerate / self.jack_client.blocksize )
	
	def addLoop (self):
		self.midi_record = False
		self.curr_loop = Loop ( str (len(self.loops)), self.jack_client, self )
		self.loops.append (self.curr_loop)
	
	def addLoops (self, n):
		for i in range(n):
			self.addLoop()
	
	def deleteCurrLoop (self):
		self.curr_loop ('delete')
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
			self.curr_loop.log ('new current loop')
			
			if not self.isMaster (self.curr_loop) and len (self.sync_loop.samples) == 0:
				print ('change sync loop')
				self.set_sync_loop (self.curr_loop)
		else:
			self.log ('warning: no such loop')
	
	def set_sync_loop (self, l):
		self.sync_loop = l		
		l.log ('new master')
	
	def selectNextLoop (self):
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i + 1) % len(self.loops)
		
		self.setCurrLoop (i)
		
	def selectPrevLoop (self):
		self.midi_record = False
		i = self.loops.index (self.curr_loop)
		i = (i - 1) % len(self.loops)
		self.setCurrLoop (i)
	
	def toggleRecord (self):
		if self.record_counter == 0:
			if self.curr_loop.state == 'play':
				self.curr_loop.stop()
			
		elif self.record_counter == 1:
			self.curr_loop.log ('stop recording')
			
			self.curr_loop.applyRecord() # copy temp samples to real samples
			
			if looper.isMaster (self.curr_loop):
				for l in self.getSlaveLoops():
					if len (l.curr_sample) > 0:
						l.sync_samples = [looper.sync_loop.curr_sample[0]]
			
			if len (self.curr_loop.samples) >= self.buffer.maxlen * 2:
				if self.curr_loop != self.sync_loop:
					
					if self.curr_loop.getSyncMode() == 'continous':
						self.syncManager.calc_sync_samples (self.sync_loop, self.curr_loop)
				else: # self.curr_loop == self.sync_loop
					if self.curr_loop.getSyncMode() == 'continous':
						for l in self.loops:
							if l != self.curr_loop  and l.state != 'empty':
								self.syncManager.calc_sync_samples (self.sync_loop, l)
					
							l.sync_samples = []
							break
				
				self.curr_loop.stopRecord()
			else:
				self.curr_loop.log ('warning: loop length is smaller than 2 * buffer_size, dropping loop')
				self.curr_loop.samples = []
				self.curr_loop.state = 'empty'
			
			
	
		self.record_counter = (self.record_counter + 1) %  2
			
	def dropRecording (self):
		self.record_counter = 0
		self.curr_loop.dropRecording()
	
	def toggleRecordMidi (self):
		midi_track = self.curr_loop.getCurrMidiTrack()
		
		if midi_track != None:
			if not self.midi_record:
				self.curr_loop.log ('start midi record')
				self.curr_loop.getCurrMidiTrack().isPlaying = False
				self.curr_loop.getCurrMidiTrack().enabled = False
				self.curr_loop.getCurrMidiTrack().samples = {}
				self.curr_loop.getCurrMidiTrack().sync_sample = -1
			else:
				self.curr_loop.log ('end midi record')
				self.curr_loop.getCurrMidiTrack().enabled = True
				
			self.midi_record = not self.midi_record
	
	def getSlaveLoops (self):
		return [l for l in self.loops if l != self.sync_loop]
	
	def setRecordMode (self, mode):
		self.record_mode = mode
		self.record_counter = 0
	
	def isMaster (self, loop):
		return self.sync_loop == loop
	
	def log (self, msg):
		if self.debug:
			print (msg)
			

argParser = argparse.ArgumentParser()
argParser.add_argument('-l', '--loops', default=8, metavar='N', type=int, help='create N initial loops, default=8')	
argParser.add_argument('-i', '--input', help='toggle record on stdin input', action='store_true')	
argParser.add_argument('-b', '--buffer', help='buffer size in milliseconds. Results in smooth transition between loop cycles. Higher values may leed to undesired results. Values higher than 500 do not make any sense. The minimum length of a loop has to longer than 2 times this value.', type=int,  default=300, metavar='N')	
argParser.add_argument('-d', '--deviation', help='allowed unpreciseness in seconds', type=float,  default=0.6, metavar='N')	
argParser.add_argument('-t', '--threshold', help='audio signal threshold at which recording starts after sending the record command', type=float,  default=0.05, metavar='N')	
argParser.add_argument('-v', '--verbose', help='debugging mode',  action='store_true')	
args = argParser.parse_args()

looper = Looper (args.loops, args.buffer)
looper.record_treshhold = args.threshold
looper.deviation = args.deviation
looper.debug = args.verbose
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
	b = copy.deepcopy ( looper.inport.get_array() )
	looper.buffer.append (b) # ring buffer
	
	curr_loop = looper.curr_loop
	if looper.record_counter == 1:
		if curr_loop.state != 'record' and max(b) > looper.record_treshhold:
			curr_loop.state = 'record'
			
			# faid in head buffer
			curr_loop.temp_head_buffer = looper.buffer
			
			if not looper.isMaster (curr_loop) and len (looper.sync_loop.curr_sample) > 0:
				# sync_samples should be empty list here
				# TODO: test this line:
				#curr_loop.sync_samples = [curr_loop.sync_loop.curr_sample]
				curr_loop.temp_sync_samples.append (looper.sync_loop.curr_sample[0])
						
			curr_loop.log ('recording')
		
		if curr_loop.state == 'record':
			curr_loop.setData (b)
	
	# record midi
	if looper.midi_record:
		for offset, data in looper.midi_inport.incoming_midi_events():
			b1, b2, b3 = struct.unpack('3B', data)
			if len(data) == 3:
				if len (curr_loop.curr_sample) > 0:
					curr_loop.getCurrMidiTrack().setDataFromMidi (data, curr_loop.curr_sample[0])
		
	for loop in looper.loops:
		# wav play
		playNullSample = True
		if loop.state == 'play':
			# append tail_buffer if needed
			if len (loop.tail_buffer) < len (looper.buffer):
				loop.tail_buffer.append (b)
				loop.log (f'{loop.state=}')
				loop.log (f'{len (loop.tail_buffer)=}')
				loop.log (f'{len (looper.buffer)=}')
				if len (loop.tail_buffer) >= len (looper.buffer):
					
					# fade out tail_buffer
					loop.tail_buffer[:] = [loop.tail_buffer[i] * m for i, m in enumerate ( np.linspace ( 1, 0, num=len (loop.tail_buffer) ) )]
						
					loop.samples = loop.samples + loop.tail_buffer
					loop.log ('samples after add tail_buffer: %s' % len(loop.samples) )
			
			if looper.isMaster (loop):
				if len (loop.curr_sample) == 0:
					loop.addPlayInstance()
					# for first play after record start loop from record start without playing the head_buffer
					loop.curr_sample[0] = len (loop.head_buffer)
				elif len (loop.curr_sample) == 1:
					if loop.curr_sample[0] >= len (loop.samples) - len (loop.tail_buffer) - len (loop.head_buffer):
						loop.addPlayInstance()
			
			else: # not looper.isMaster (loop):
				add = False
				for cs in looper.sync_loop.curr_sample: # should be only 1 item
					
					if ( len (loop.curr_sample) == 0 or loop.curr_sample[-1] >= len (loop.samples) - len (loop.head_buffer) - looper.deviation_samples ) and cs in loop.sync_samples:
						loop.addPlayInstance()
						add = True
						break
			
				# add play instance right after recording without wait for the next cycle to start
				if not add:
					if len (loop.curr_sample) == 0:
						for ss in reversed (loop.sync_samples):
							for cs in looper.sync_loop.curr_sample:
								if cs > ss:
									loop.log ('start early play instance')
									loop.addPlayInstance (cs - ss)
									break
			
			if loop == looper.sync_loop or \
				len (loop.curr_sample) > 0 or \
			   ( len (looper.sync_loop.curr_sample) > 0 and \
			    looper.sync_loop.curr_sample[0] in loop.sync_samples ):
					
				loop.isPlaying = loop.nextSample()
				
				if not loop.mute:
					loop.outport.get_array()[:] = loop.getData (frames)
					playNullSample = False
				
		if playNullSample:
			if not loop.grounded:
				loop.log ('grounding')
				loop.outport.get_array()[:] = null_sample
				loop.grounded = True
		
		# midi play
		for mt in loop.midi_tracks:
			mt.midi_outport.clear_buffer()
			
			#if mt.enabled and (mt.isPlaying or mt.sync_sample == loop.curr_sample):
			if mt.enabled:
				if len (loop.curr_sample) > 0:
					### TODO: handle midi tracks which are longer than wav loop
					data = mt.getData (loop.curr_sample[0])
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
				print('press enter to toggle record')
				input()
				looper.toggleRecord()
			
				time.sleep (0.1);
			else:
				time.sleep (1000)
