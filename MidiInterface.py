from midi_map import midi_map

class MidiInterface:
	def __init__(self, looper):
		self.looper = looper
		self.midi_inport = looper.jack_client.midi_inports.register ('midi_control')
		
		self.cmd_map = {
			'select_loop_0': lambda: looper.setCurrLoop (0),
			'select_loop_1': lambda: looper.setCurrLoop (1),
			'select_loop_2': lambda: looper.setCurrLoop (2),
			'select_loop_3': lambda: looper.setCurrLoop (3),
			'select_loop_4': lambda: looper.setCurrLoop (4),
			'select_loop_5': lambda: looper.setCurrLoop (5),
			'select_loop_6': lambda: looper.setCurrLoop (6),
			'select_loop_7': lambda: looper.setCurrLoop (7),
			
			'toggle_midi_track_0_mute': lambda: self.toggle_midi_track_mute (0),
			'toggle_midi_track_1_mute': lambda: self.toggle_midi_track_mute (1),
			'toggle_midi_track_2_mute': lambda: self.toggle_midi_track_mute (2),
			'toggle_midi_track_3_mute': lambda: self.toggle_midi_track_mute (3),
			'toggle_midi_track_4_mute': lambda: self.toggle_midi_track_mute (4),
			'toggle_midi_track_5_mute': lambda: self.toggle_midi_track_mute (5),
			'toggle_midi_track_6_mute': lambda: self.toggle_midi_track_mute (6),
			'toggle_midi_track_7_mute': lambda: self.toggle_midi_track_mute (7),
			
			'new_loop': lambda: looper.addLoop(),
			'delete_loop': lambda: looper.deleteCurrLoop(),
			'select_next_loop': lambda: looper.selectNextLoop(),
			'select_prev_loop': lambda: looper.selectPrevLoop(),
			
			'toggle_record': lambda: looper.toggleRecord(),
			
			'toggle_midi_track_mute': lambda: looper.curr_loop.getCurrMidiTrack().toggleEnable(),
			'toggle_loop_mute': lambda: looper.curr_loop.toggleMute(),
			
			'new_midi_track': lambda: looper.curr_loop.addMidiTrack(),
			'delete_midi_track': lambda: looper.curr_loop.deleteCurrMidiTrack(),
			'select_next_midi_track': lambda: looper.curr_loop.selectNextMidiTrack(),
			'select_prev_midi_track': lambda: looper.curr_loop.selectPrevMidiTrack(),
			
			'toggle_record_midi': lambda: looper.toggleRecordMidi(),
			
			'toggle_sync_mode': lambda: looper.curr_loop.toggleSyncMode(),
			
			'clear_curr_loop': lambda: self.clear_curr_loop(),
			'stop_curr_loop': lambda: looper.curr_loop.stop(),
			
			'drop_record': lambda: looper.dropRecording(),
		}
		
		self.cmd_map_arg = {
			'set_volume_loop_0': lambda vol: self.setVol (0, vol),
			'set_volume_loop_1': lambda vol: self.setVol (1, vol),
			'set_volume_loop_2': lambda vol: self.setVol (2, vol),
			'set_volume_loop_3': lambda vol: self.setVol (3, vol),
			'set_volume_loop_4': lambda vol: self.setVol (4, vol),
			'set_volume_loop_5': lambda vol: self.setVol (5, vol),
			'set_volume_loop_6': lambda vol: self.setVol (6, vol),
			'set_volume_loop_7': lambda vol: self.setVol (7, vol),
			'set_volume': lambda vol: looper.curr_loop.setVolume (vol)
		}
	
	def clear_curr_loop (self):
		self.looper.curr_loop.clear (self.looper)
		self.looper.record_counter = 0
	
	def toggle_midi_track_mute (self, l):
		ct = self.looper.loops[l].getCurrMidiTrack()
		if ct:
			ct.toggleEnable(),
	
	def setVol (self, loop, vol):
		if loop >= 0 and loop < len(self.looper.loops):
			self.looper.loops[loop].setVolume (vol)
	
	def executeMidiCmd (self, cmd, arg):
		if cmd in midi_map:
			if midi_map[cmd] in self.cmd_map:
				if arg == 127:
					self.cmd_map[midi_map[cmd]]()
			elif midi_map[cmd] in self.cmd_map_arg:
				self.cmd_map_arg[midi_map[cmd]](arg)
		#else:
		#	print (cmd, arg)
	
	def linearTrans (x1, x2, a, b, c):
		return x1 + ((x2 - x1)/(b - a)) * (c - a)

			
	
