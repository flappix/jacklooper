#!/usr/bin/env python3

import jack
import random
import numpy
from aubio import notes
import copy
from loop import Loop
from SyncManager import SyncManager
		

jack_client = jack.Client('Looper')
inport = jack_client.inports.register ('in')

loops = [Loop ('0', jack_client, 'master')]
curr_loop = loops[0]
sync_loop = loops[0]
record = False
playback = False
midi_control_record = False

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
	
	if midi_control_record:
		for offset, data in midi_inport.incoming_midi_events():
			if len(data) == 3:
				curr_loop.setMidiData (data, curr_loop.curr_sample)
		
	# play-1
	
	# master loop only
	ml = loops[0]
	if ml.state == 'play':
		ml.nextSample()
		ml.outport.get_array()[:] = ml.getData (frames)
	
	# non-master loops only
	for loop in loops[1:]:
		loop.midi_outport.clear_buffer()
		
		if loop.state == 'play':
			if loop.isPlaying or loop.sync_loop.curr_sample in loop.sync_samples:
				
				loop.isPlaying = True
				loop.nextSample()
				loop.outport.get_array()[:] = loop.getData (frames)
				
				if loop.playMidi and loop.curr_sample in loop.midi_samples:
					loop.midi_outport.write_midi_event (0, (144, loop.midi_samples[loop.curr_sample][0], 127))

				
				if loop.curr_sample == len(loop.samples) - 1:
					loop.isPlaying = False
			else:
				loop.outport.get_array()[:] = null_sample
	
	# both
	for loop in loops:
		loop.midi_control_outport.clear_buffer()
		
		if loop.playMidiControl:
			for cs in loop.midi_control_samples:
				if loop.curr_sample in cs:
					loop.midi_control_outport.write_midi_event (0, cs[loop.curr_sample])

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
				
			# convert to midi
			o = notes('default', buf_size=256, hop_size=256, samplerate=44100)
			#o.set_threshold (0.7)
			o.set_silence (-30)
			
			for k in range(len(curr_loop.samples)):
				s = curr_loop.samples[k]
				new_note = o(s)
				if new_note[0] != 0:
					curr_loop.midi_samples[k] = copy.deepcopy (new_note)
					print(new_note)
					#print("%.6f" % (total_frames/float(samplerate)), new_note)
					#print (o.get_last())
			curr_loop.playMidi = True
			curr_loop.log (curr_loop.midi_samples)
		
		curr_loop.state = 'play'
		
		curr_loop.addMidiControlSample()
		print ('press enter to start midi control record')
		input()
		midi_control_record = True
		print ('press enter to exit midi control record')
		input()
		midi_control_record = False
		curr_loop.playMidiControl = True

		
		curr_loop = Loop ( str (i), jack_client, sync_loop )
		loops.append (curr_loop)
		
		i += 1
