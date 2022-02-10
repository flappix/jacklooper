# jacklooper
Headless audio looper, controllable via MIDI. Under development.

## Features

* wav looping
  * synchronization
* midi looping
  * notes and cc events
* controllable via midi

## Requirements

* Jack2
* Python 3
	* numpy ```pip install numpy```
	* jackclient-python ```pip install JACK-Client```

## Usage

Run ```python looper.py```.  
Use ```-l <n>``` switch to start with n number of initial loops. By default 8 loops are created.

Connect your midi controller to the midi input port ```midi_control``` to send  commands like ```record```, ```select loop```, etc. to jacklooper.  
Connect your midi controller to the midi input port ```midi_capture``` to record and loop midi events.

### Looping
Each loop has its own jack output port which has to be connected to its target separately. Each loop can have an unlimited number of midi tracks which may contain any midi data (notes, CC, ...). These midi tracks are looped along with the loop they are associated with. Each midi track has its own jack midi output port and has to be connected to its target separatley.

## Configuration

Modify ```midi_map.py``` to map a midi CC event to a jacklooper command.

## Record modes

Jacklooper implements three different record modes which can be changed via ```record_mode_*``` commands (see commands section for details).

* ***default***: [toggle_record] -> recording -> [toggle_record] -> playing -> [toggle_record] -> recording -> [toggle_record] -> playing -> ...
* ***delete***: [toggle_record] -> recording -> [toggle_record] -> playing -> [toggle_record] -> clear loop -> [toggle_record] -> recording -> ...
* ***pause***: [toggle_record] -> recording -> [toggle_record] -> playing -> [toggle_record] -> pause loop -> [toggle_record] -> playing -> [toggle_record] -> pause loop -> [toggle_record] -> playing -> ...

### commands 

|command | description|
|--------|------------|
|select_loop_0|sets current loop to loop 0|
|select_loop_1|sets current loop to loop 1|
|select_loop_2|sets current loop to loop 2|
|select_loop_3|sets current loop to loop 3|
|select_loop_4|sets current loop to loop 4|
|select_loop_5|sets current loop to loop 5|
|select_loop_6|sets current loop to loop 6|
|select_loop_7|sets current loop to loop 7|
|select_prev_loop|sets current loop to the previous one. If current loop is the first one the last one will be selected|
|select_next_loop|sets current loop to the next one. If current loop is the last one the first one will be selected|
|new_loop|adds a new loop and select it as current loop|
|delete_loop|deletes the current loop. Selects the previous loop as the current loop after deletion|
|toggle_loop_mute|mutes/unmutes the current loop|
|new_midi_track|adds a new midi track to the current loop and selects it as the current midi track|
|delete_midi_track|deletes current midi track of the current loop. The previous one will be selected as current midi track after deletion|
|select_prev_midi_track|sets the current midi track of the current loop to the previous one. If current midi track is the first one the last one will be selected|
|select_next_midi_track|sets the current midi track of the current loop to the prev one. If current midi track is the last one the first one will be selected|
|toggle_record|starts/ends recording the current loop|
|toggle_midi_record|starts/ends recording the current midi track of the current loop|
|toggle_midi_track_mute|mutes/unmutes the current midi track of the current loop|
|toggle_sync_mode|switches the sync mode for the current loop between ```gap``` and ```continous```|
|record_mode_default|sets record mode to default|
|record_mode_delete|sets record mode to delete|
|record_mode_pause|sets record mode to pause|
|clear_curr_loop|clears the current loop|
|set_volume_loop_0 <vol>|sets volume for loop 0|
|set_volume_loop_0 <vol>|sets volume for loop 1|
|set_volume_loop_0 <vol>|sets volume for loop 2|
|set_volume_loop_0 <vol>|sets volume for loop 3|
|set_volume_loop_0 <vol>|sets volume for loop 4|
|set_volume_loop_0 <vol>|sets volume for loop 5|
|set_volume_loop_0 <vol>|sets volume for loop 6|
|set_volume_loop_0 <vol>|sets volume for loop 7|
|set_volume <vol>|sets volume for current loop|
