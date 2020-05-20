#!/usr/bin/env python3

import jack
import math
import random
import copy
import numpy
from decimal import Decimal

class Loop:
	def __init__(self, _name, jack_client, _sync_loop):
		self.name = _name
		self.samples = []
		self.curr_sample = -1
		self.outport = jack_client.outports.register ( "out" + str (self.name) )
		self.sync_loop = _sync_loop
		self.sync_samples = []
		self.state = 'empty' # empty, record, play
		self.isPlaying = False
			

	def setData (self, data, pos=None):
		if pos == None:
			self.samples.append ( copy.deepcopy (data) )
		else:
			self.samples[pos] = data;
	
	def getData (self, frames):
		if self.samples != None:
			return self.samples[self.curr_sample]
		
		return [0] * frames
	
	def nextSample (self):
		self.curr_sample = (self.curr_sample + 1) % len (self.samples)
		return self.curr_sample == 0
		
	def log (self, msg):
		print ('loop ' + str(loop.name) + ': ' + str(msg))
		

jack_client = jack.Client('Looper')
inport = jack_client.inports.register ('in')

loops = [Loop ('0', jack_client, 'master')]
curr_loop = loops[0]
sync_loop = loops[0]
record = False
playback = False

record_treshhold = 0.05


def create_fractions (n):
	fractions = [(k/i, k, i) for i in range(1,n+1) for k in range (1,i)]
	delete = []
	for f in fractions:
		for k in fractions:
			if f != k and f[0] == k[0]:
				if f[2] < k[2]:
					delete.append (k)
				else:
					delete.append (f)
					
	fractions = [f for f in fractions if f not in delete]
	
	fractions.sort(key=lambda x: x[0])
	return [(0, 0, 1)] + fractions + [(1, 1, 1)]
			
	
def quantize (master_length, curr_length, fractions):
	q = curr_length / master_length
	qq = q % 1
	
	for i in range(len(fractions)):
		if qq < fractions[i][0]:
			
			if abs(qq - fractions[i-1][0]) < abs(fractions[i][0] - qq):
				return (math.floor(q) + fractions[i-1][0], fractions[i][2])
			else:
				return (math.floor(q) + fractions[i][0], fractions[i][2])

q_fractions = create_fractions (4)	


@jack_client.set_process_callback
def process (frames):
	global loop
	global curr_loop
	global record
	
	null_sample = [0] * frames

	if record:
		b = inport.get_array()
		if curr_loop.state != 'record' and max(b) > record_treshhold:
			curr_loop.state = 'record'
			if curr_loop.sync_loop != 'master':
				# sync_samples should be empty list here
				curr_loop.sync_samples.append ( curr_loop.sync_loop.curr_sample )
			print ('recording loop ' + curr_loop.name)
		
		if curr_loop.state == 'record':
			curr_loop.setData (b)
	# play
	
	# master loop
	ml = loops[0]
	if ml.state == 'play':
		ml.nextSample()
		ml.outport.get_array()[:] = ml.getData (frames)
	
	for loop in loops[1:]:
		if loop.state == 'play':
			if loop.isPlaying or loop.sync_loop.curr_sample in loop.sync_samples:
				
				loop.isPlaying = True
				loop.nextSample()
				loop.outport.get_array()[:] = loop.getData (frames)
				
				if loop.curr_sample == len(loop.samples) - 1:
					loop.isPlaying = False
			else:
				loop.outport.get_array()[:] = null_sample

with jack_client:
	jack_client.activate()
	
	i = 1
	while True:
		input()
		print ('wait for treshold ' + curr_loop.name);
		record = True
		input()
		print ('finished recording')
		record = False
		curr_loop.state = 'transition'
		
		# calculate sync samples
		if i > 1:
			q = quantize ( len(sync_loop.samples), len(curr_loop.samples), q_fractions )
			length = q[0]
			if length > 0 and length != 1:
				for k in range(q[1] - 1):
					new_sync_sample = ( curr_loop.sync_samples[-1] + len(sync_loop.samples) * length ) % len(sync_loop.samples)
					curr_loop.sync_samples.append (new_sync_sample)
				
				curr_loop.sync_samples = [round(i) for i in curr_loop.sync_samples]
		
		curr_loop.state = 'play'
		
		curr_loop = Loop ( str (i), jack_client, sync_loop )
		loops.append (curr_loop)
		
		i += 1
