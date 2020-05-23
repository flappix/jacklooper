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
			
			'new_loop': lambda: looper.addLoop(),
			'delete_loop': lambda: looper.deleteCurrLoop(),
			'select_next_loop': lambda: looper.selectNextLoop(),
			'select_prev_loop': lambda: looper.selectPrevLoop(),
			
			'toggle_record': lambda: looper.toggleRecord(),
			
			'toggle_midi_track_enable': lambda: looper.curr_loop.getCurrMidiTrack().toggleEnable(),
			
			'new_midi_track': lambda: looper.curr_loop.addMidiTrack(),
			'delete_midi_track': lambda: looper.curr_loop.deleteCurrMidiTrack(),
			'select_next_midi_track': lambda: looper.curr_loop.selectNextMidiTrack(),
			'select_prev_midi_track': lambda: looper.curr_loop.selectPrevMidiTrack(),
			
			'toggle_record_midi': lambda: looper.toggleRecordMidi()
		}
		
	
	def executeMidiCmd (self, cmd):
		if cmd in midi_map:
			self.cmd_map[midi_map[cmd]]()
			
	
