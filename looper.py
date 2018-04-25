#!/usr/bin/env python3

import jack
import math
import random
import copy
import numpy

bpm = None
quantize = 1
tick_diff = None
frames_per_quant = None

class Loop:
	samples = []
	curr_sample = -1
	start_tick = -1
	state = 'empty' # empty, record, play
	length = 0

	def setData (self, data):
		self.samples.append ( copy.deepcopy (data) )
	

	def calc_start_tick (self, pos):
		if pos['tick'] % tick_diff < tick_diff / 2:
			self.start_tick = tick_diff * ( int (pos['tick'] / tick_diff) % quantize )
		else:
			self.start_tick = tick_diff * ( math.ceil (pos['tick'] / tick_diff) % quantize )
	
	def getData (self):
		if self.samples != None:
			#print (len(self.samples))
			#print(len(self.samples))
			#print(self.curr_sample)
			self.curr_sample = (self.curr_sample + 1) % len(self.samples)
			return self.samples[self.curr_sample]
		
		return None
	
	def computeLength (self, frames):
		if self.state == 'record':
			print ('WARNING: compute loop length, but recording is not finished')
		
		self.length = frames * len (self.samples)
	
	def resize (self):
		print ('frames per quant: ' + str(frames_per_quant)) # 124
		print ('size: ' + str (self.length)) # 111
		
		print ('new size: ' + str (
	


loops = 8
loop = [Loop() for i in range(loops)]
curr_loop = 0
record = False
playback = False

record_treshhold = 0.1

jack_client = jack.Client('Looper')
outports = [jack_client.outports.register ("out" + str(i)) for i in range (loops)]
inport = jack_client.inports.register ("in")

@jack_client.set_process_callback
def process (frames):

	global loop
	global curr_loop
	
	state, pos = jack_client.transport_query()
	
	if state == jack.ROLLING:
		if (pos['beats_per_minute'] != bpm):
			calc_sync_settings (pos)
		
		if record:
			b = inport.get_array()
			if loop[curr_loop].state != 'record' and max(b) > record_treshhold:
				loop[curr_loop].calc_start_tick (pos)
				loop[curr_loop].state = 'record'
			
			if loop[curr_loop].state == 'record':
				loop[curr_loop].setData (b)
		
		for i in range(len(loop)):
			if loop[i].state == 'play':
				if loop[i].curr_sample == 0:
					if abs (pos['tick'] - loop[i].start_tick) == 0:
						outports[i].get_array()[:] = loop[i].getData()
				else:
					outports[i].get_array()[:] = loop[i].getData()

def calc_sync_settings (pos):
	global bpm
	global tick_diff
	global frames_per_quant
	
	bpm = pos['beats_per_minute']
	tick_diff = pos['ticks_per_beat'] / quantize
	if int(tick_diff) != tick_diff:
		print ('WARNING: ticks_per_beat (' + str(pos['ticks_per_beat']) + ') cannot be devided by quantize (' + str(quantize) + ')')
	
	tick_diff = int(tick_diff)
	frames_per_quant =  (client.samplerate * 60 / bpm) / quantize
	

	
			
with jack_client:
	jack_client.activate()
	
	input()
	record = True
	
	while True:
		input()
		loop[curr_loop].state = 'play'
		
		curr_loop += 1
