from midi_map import midi_map

class MidiInterface:
	def __init__(self, looper):
		self.looper = looper
		self.midi_inport = looper.jack_client.midi_inports.register ('midi_control')
		
		self.cmd_map = {
			'select_loop_0': lambda: looper.setCurrLoop (looper.loops[0]),
			'select_loop_1': lambda: looper.setCurrLoop (looper.loops[1]),
			'select_loop_2': lambda: looper.setCurrLoop (looper.loops[2]),
			'select_loop_3': lambda: looper.setCurrLoop (looper.loops[3]),
			'select_loop_4': lambda: looper.setCurrLoop (looper.loops[4]),
			'select_loop_5': lambda: looper.setCurrLoop (looper.loops[5]),
			'select_loop_6': lambda: looper.setCurrLoop (looper.loops[6]),
			'select_loop_7': lambda: looper.setCurrLoop (looper.loops[7]),
			
			'select_next_loop': lambda: looper.setCurrLoop ( (looper.curr_loop + 1) % len(looper.loops) ),
			'select_prev_loop': lambda: looper.setCurrLoop ( (looper.curr_loop - 1) % len(looper.loops) ),
			
			'toggle_record': lambda: looper.toggleRecord(),
			
			'toggle_wav2midi': lambda: looper.curr_loop.midi_tracks[0].setEnabled (not looper.curr_loop.midi_tracks[0].enabled),
			
			'toggle_record_midi_track': lambda: looper.recordNewMidiTrack()
		}
		
	
	def executeMidiCmd (self, cmd):
		if cmd in midi_map:
			self.cmd_map[midi_map[cmd]]()
			
	
