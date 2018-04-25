#!/usr/bin/env python3

import jack
client = jack.Client('Klick')
frame_counter = 0

@client.set_process_callback
def process (f):
	global frame_counter
	state, pos = client.transport_query()
	
	if state == jack.ROLLING:
		frame_counter += f
		
		# how many frames are get processed in 1 beat?
		frames_per_beat = client.samplerate * 60 / pos['beats_per_minute']
		
		# did we process enough frames for 1 beat?
		if frame_counter >= frames_per_beat:
			print ('klick')
			frame_counter -= frames_per_beat
		 
			
with client:
	client.activate()
	input()
