#!/usr/bin/env python

# Test of the audiocapture module

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 01.08.2018

from audiocapture import SoundRecorder
import time
import csv

RECORD_DURATION = 15
MINIMUM_SOUND_DURATION = 0.100
AUDIO_RECORD_FILE = "./test_audio_record"
EVENTS_FILE = "./test_audio_event.csv"

def main():
    print("INFO: Start audio test.")
    
    # Initialize audio recorder
    soundEventHandler = SoundEventHandler()
    recorder = SoundRecorder(handler=soundEventHandler,
                             threshold_level_onset=100,
                             threshold_level_offset=100,
                             onset_window=5,
                             offset_window=5)
    print("INFO: Initialize sound recorder.")
    recorder.initRecorder()
    time.sleep(2)
    # Start record and wait for termination
    print("INFO: Start recording.")
    call_start_clock_time = time.clock()
    recorder.startRecording(filename=AUDIO_RECORD_FILE, 
                            duration=RECORD_DURATION)
    return_start_clock_time = time.clock()
    while (recorder.isRecording()):
        time.sleep(1)
    print("INFO: End of record.")
    
    # Save result
    with open(EVENTS_FILE, 'wb') as fw:
        writer = csv.writer(fw, delimiter = '\t')
        # Header
        writer.writerow(["Call start clock time", call_start_clock_time])
        writer.writerow(["Return start clock time", return_start_clock_time])
        for event in soundEventHandler.events:
            writer.writerow(event)
    print("INFO: End of audio test.")
    
class SoundEventHandler:
    
    def __init__(self):
        self.events = []
        self.last_onset = None
        
    def onSoundEvent(self, sound_event):
        
        event_str = "onset" if sound_event.onset else "offset"
        self.events.append([event_str, sound_event.elapsed])
        print("Sound event: "+event_str)
        # Check sound duration
        if not sound_event.onset and self.last_onset is not None:
            sound_duration = sound_event.elapsed - self.last_onset.elapsed
            if sound_duration < MINIMUM_SOUND_DURATION:
                self.events.append(["Discarded sound", self.last_onset.elapsed, 
                                    sound_event.elapsed, sound_duration])
                '''
                print("Discarded sound, start: "+
                      str(round(self.last_onset.elapsed,3))+
                      ", duration: "+
                      str(round(sound_duration,3)))
                '''
            else:
                self.events.append(["Valid sound", self.last_onset.elapsed, 
                                    sound_event.elapsed, sound_duration])
                print("VALID SOUND, start: "+
                      str(round(self.last_onset.elapsed,3))+
                      ", duration: "+
                      str(round(sound_duration,3)))
        # Keep last onset event
        if sound_event.onset:
            self.last_onset = sound_event
        
if __name__ == '__main__':
    main()
