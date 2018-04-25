#!/usr/bin/env python3

import jack
import math
import random
import copy
import numpy

class Loop:
	samples = []
	curr_sample = -1
	start_tick = -1
	state = 'empty' # empty, record, play

	def setData (self, data):
		self.samples.append ( copy.deepcopy (data) )
	
	def setStartTick (self, tick):
		self.start_tick = tick
	
	def getData (self):
		if self.samples != None:
			#print (len(self.samples))
			#print(len(self.samples))
			#print(self.curr_sample)
			self.curr_sample = (self.curr_sample + 1) % len(self.samples)
			return self.samples[self.curr_sample]
		
		return None
	


loops = 8
loop = [Loop() for i in range(loops)]
curr_loop = 0
record = False
playback = False

record_treshhold = 0.1

bpm = -1
quantize = 1
fields = []
tick_diff = -1

jack_client = jack.Client('Looper')
outports = [jack_client.outports.register ("out" + str(i)) for i in range (loops)]
inport = jack_client.inports.register ("in")

@jack_client.set_process_callback
def process(frames):
	print(frames)
	global loop
	global curr_loop
	
	state, pos = jack_client.transport_query()
	
	if state == jack.ROLLING:
		if (pos['beats_per_minute'] != bpm):
			calc_sync_settings (pos)
		
		if record:
			b = inport.get_array()
			if loop[curr_loop].state != 'record' and max(b) > record_treshhold:
				adj_tick = calc_start_tick (pos)
				print(adj_tick)
				loop[curr_loop].setStartTick (adj_tick)
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
	
	fields = [ i * pos['ticks_per_beat'] / quantize for i in range (0, quantize) ]
	bpm = pos['beats_per_minute']
	tick_diff = pos['ticks_per_beat'] / quantize
	if int(tick_diff) != tick_diff:
		print ('WARNING: ticks_per_beat (' + str(pos['ticks_per_beat']) + ') cannot be devided by quantize (' + str(quantize) + ')')
	
	tick_diff = int(tick_diff)
	
def calc_start_tick (pos):
	print(pos['tick'])
	print(tick_diff)
	print(quantize)
	
	if pos['tick'] % tick_diff < tick_diff / 2:
		return tick_diff * ( int (pos['tick'] / tick_diff) % quantize )
	else:
		return tick_diff * ( math.ceil (pos['tick'] / tick_diff) % quantize )
	#
	#x = pos['tick'] / tick_diff
	#return tick_diff * ( ( int (x) if pos['tick'] % tick_diff < tick_diff / 2 else math.ceil (x) ) % quantize )
	
	#pos['tick'] % (pos['ticks_per_bar'] / quantize)
	
	#for i in range (len(fields)):
	#	if pos['tick'] <= fields[i]:
	#		if fields[i] - pos['tick'] < tick_diff / 2:
	#			return fields[i]
	#		else:
	#			return fields[i-1]
	
	# current tick is greater then the last field entry
	#if pos['tick'] - fields[-1] < tick_diff / 2:
	#	return fields[-1]
	#else:
	#	return 0

#def resize_sample():
	
			
with jack_client:
	jack_client.activate()
	
	input()
	record = True
	
	while True:
		input()
		loop[curr_loop].state = 'play'
		
		curr_loop += 1
