#!/usr/bin/env python3

import jack
import random
import numpy
from loop import Loop
from SyncManager import SyncManager
		

jack_client = jack.Client('Looper')
inport = jack_client.inports.register ('in')

loops = [Loop ('0', jack_client, 'master')]
curr_loop = loops[0]
sync_loop = loops[0]
record = False
playback = False
midi_record = False

record_treshhold = 0.05

syncManager = SyncManager()

midi_inport = jack_client.midi_inports.register ('midi_input')

@jack_client.set_process_callback
def process (frames):
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
	
	if midi_record:
		for offset, data in midi_inport.incoming_midi_events():
			if len(data) == 3:
				curr_loop.getCurrMidiTrack().setDataFromMidi (data, curr_loop.curr_sample)
				curr_loop.getCurrMidiTrack().sync_sample = curr_loop.curr_sample
				#print('sync sample: ' + curr_loop.getCurrMidiTrack().sync_sample)
		
	# play-1
	
	# master loop only
	ml = loops[0]
	if ml.state == 'play':
		ml.nextSample()
		ml.outport.get_array()[:] = ml.getData (frames)
	
	# non-master loops only
	for loop in loops[1:]:
		
		if loop.state == 'play':
			if loop.isPlaying or loop.sync_loop.curr_sample in loop.sync_samples:
				
				loop.isPlaying = loop.nextSample()
				loop.outport.get_array()[:] = loop.getData (frames)
			else:
				loop.outport.get_array()[:] = null_sample
	
	# both
	for loop in loops:
		for mt in loop.midi_tracks:
			mt.midi_outport.clear_buffer()

			if mt.enabled and (mt.isPlaying or mt.sync_sample == loop.curr_sample):
				mt.isPlaying = mt.nextSample()
				data = mt.getData()
				if data != None:
					mt.midi_outport.write_midi_event (0, data)
					
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
			syncManager.calc_sync_samples (sync_loop, curr_loop)
		
		curr_loop.convertWav2Midi()
		curr_loop.getCurrMidiTrack().enabled = True
		curr_loop.state = 'play'
		
		curr_loop.addMidiTrack()
		print ('press enter to start midi control record')
		input()
		midi_record = True
		print ('press enter to exit midi control record')
		input()
		midi_record = False
		curr_loop.getCurrMidiTrack().enabled = True

		
		curr_loop = Loop ( str (i), jack_client, sync_loop )
		loops.append (curr_loop)
		
		i += 1
