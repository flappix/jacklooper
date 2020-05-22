# jacklooper
Headless audio looper, controllable via MIDI. Under development.

## Features

* wav looping
  * synchronization
* midi looping
  * notes and cc events
* wav to midi conversion
* controllable via midi

## Requirements

* Python 3.6
* Jack
* Aubio

## Usage

Run ```python looper.py```.  
Connect your midi controller to the midi input port ```midi_control``` to send controll commands like ```record```, ```select loop```, etc. to jacklooper.  
Connect your midi controller to the midi input port ```midi_capture``` to record and loop midi events.

## Configuration

Modify ```midi_map.py``` to map a midi CC event to a jacklooper command.
