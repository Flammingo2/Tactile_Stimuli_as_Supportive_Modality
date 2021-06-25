# Module for recording sound.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 31.07.2018

import psychopy.voicekey
from psychopy.voicekey import _BaseVoiceKey
import threading

class SoundRecorder(object):
    """
    The sound recorder is responsible for recording sound and generating events
    when a given sound level is reached.
    
    Required module
    ---------------
    This module requires psychoPy (http://www.psychopy.org) and Pyo 
    (http://ajaxsoundstudio.com/software/pyo/).
    
    """


    def __init__(self, handler, sampleRate=44100, threshold_level_onset=150,
                 threshold_level_offset=100, onset_window=25, offset_window=25):
        """
        Constructor.
        
        Parameters
        ----------
        :param SoundEventHandler handler:
            The handler for sound events.
        :param int sampleRate:
            Sample rate for recording.
        :param int threshold_level_onset:
            The threshold level for detecting onset.
        :param int threshold_level_offset:
            The threshold level for detecting offset.
        :param int onset_window:
            Window for onset condition. One unit is 2 ms.
        :param int offset_window:
            Window for offset condition. One unit is 2 ms.
        """
        # Sample rate
        self._record_sample_rate = sampleRate
        # Threshold levels
        self._threshold_level_onset = threshold_level_onset
        self._threshold_level_offset = threshold_level_offset
        self._onset_window=onset_window
        self._offset_window=offset_window
        # Threshold detector
        self._threshold_detector = None
        # Event queue
        self._event_handler = handler
        self._event_queue = None

    def initRecorder(self):
        """
        Initializes the record service.
        """
        psychopy.voicekey.pyo_init(rate=self._record_sample_rate)
    
    def startRecording(self, filename, duration):
        """
        Starts recording.
        :param str filename:
            The filename to save the record.
        :param int duration:
            The maximum duration in seconds.
        """
        if (self._threshold_detector is None or 
            not self._threshold_detector.started):
            # Start event queue
            self._event_queue = _AsyncEventQueue(handler=self._event_handler)
            self._event_queue.start()
            # Start record
            self._threshold_detector = _ThresholdDetector(
                recorder=self,
                file_out=filename,
                duration=duration,
                threshold_level_onset=self._threshold_level_onset,
                threshold_level_offset=self._threshold_level_offset,
                onset_window=self._onset_window,
                offset_window=self._offset_window,
                event_queue=self._event_queue)
            self._threshold_detector.start()
        else:
            print("WARNING: Recorder already started.")
            
    def isRecording(self):
        """Returns the recording state.
        """
        return (self._threshold_detector is not None and 
            self._threshold_detector.started and
            not self._threshold_detector.stopped)
        
    def stopRecording(self):
        """
        Stops recording.
        """
        if (self._threshold_detector is not None and 
            self._threshold_detector.started):
            self._threshold_detector.stop()
            self._threshold_detector = None
        else:
            print("WARNING: No recorder to stop.")
        
    def addAudioMaker(self):
        """
        Adds an audio marker.
        """
        print("TODO: Add audio marker")
        
class _ThresholdDetector(_BaseVoiceKey):
    """Class for detecting onset and offset based on a threshold.
    """
    
    def __init__(self, recorder, file_out, duration, threshold_level_onset,
                 threshold_level_offset, onset_window, offset_window, 
                 event_queue):
        """
        Constructor.
        
        Parameters
        ----------
        :param SoundRecorder recorder:
            The sound recorder.
        :param int threshold:
            The threshold for detecting onset.
        """
        super(_ThresholdDetector, self).__init__(
            file_out=file_out, sec=duration, config={'more_processing': False})
        self._sound_recorder = recorder
        self._threshold_level_onset = threshold_level_onset
        self._threshold_level_offset = threshold_level_offset
        self._onset_window = onset_window
        self._offset_window = offset_window
        # Event queue
        self._event_queue = event_queue
        # Detection state
        self._active_onset = False
        
    def detect(self):
        """Overwrites the detect method to generate onset and offset events.
        """
        if (self._active_onset):
            # Check for offset
            threshold = self._threshold_level_offset * self.baseline
            conditions = all([x < threshold for x in 
                              self.power_bp[-self._offset_window:]])
            if conditions:
                # offset event
                self._active_onset = False
                event_onset = False
                event_lag = self._offset_window * self.msPerChunk / 1000.
                event_elapsed = self.elapsed - event_lag
                self._event_queue.notifySoundEvent(SoundEvent(
                    onset=event_onset, 
                    lag=event_lag,
                    elapsed=event_elapsed))
        else:
            # Check for onset
            if len(self.power_bp) < self._onset_window:
                # Not enough data
                return
            threshold = self._threshold_level_onset * self.baseline
            conditions = all([x > threshold for x in 
                              self.power_bp[-self._onset_window:]])
            if conditions:
                # onset event
                self._active_onset = True
                event_onset = True
                event_lag = self._onset_window * self.msPerChunk / 1000.
                event_elapsed = self.elapsed - event_lag
                self._event_queue.notifySoundEvent(SoundEvent(
                    onset=event_onset, 
                    lag=event_lag,
                    elapsed=event_elapsed))
    def stop(self):
        """Overrides stop method of the recorder to automatically stop the async
        queue.
        """
        _BaseVoiceKey.stop(self)
        self._event_queue.stop_flag = True

class SoundEvent(object):
    """A sound event.
    """
    
    def __init__(self, onset, lag, elapsed):
        """Constructor.
        """
        self.onset = onset
        self.lag = lag
        self.elapsed = elapsed

class _AsyncEventQueue(threading.Thread):
    """A queue of events that are processed asynchronously.
    """
    
    def __init__(self, handler):
        """ Constructor.
        
        Parameters
        ----------
        :param object eventHandler:
            The handler of sound events.
        """
        self._event_handler = handler
        # Flag for stopping the thread
        self.stop_flag = True
        # Initialize the thread
        threading.Thread.__init__(self)
        # Lock for queue
        self._queue_lock = threading.Condition()
        # Event  queue
        self._event_queue = []
    
    def run(self):
        """Thread procedure"""
        self.stop_flag = False
        print("Start _AsyncEventQueue thread.")
        while not self.stop_flag:
            with self._queue_lock:
                while len(self._event_queue) > 0:
                    # Notify next event in queue
                    event = self._event_queue[0]
                    del self._event_queue[0]
                    try:
                        if self._event_handler is not None:
                            self._event_handler.onSoundEvent(event)
                    except Exception as e:
                        print("Unable to call 'onSoundEvent' on delegate.")
                        print(str(e))
                        self.stop_flag = True
                # Wait for an item in queue
                # Note: Lock must has been acquired to wait
                self._queue_lock.wait(1)
        # Clear reference in controller
        print("Stop _AsyncEventQueue  thread.")
    
    def notifySoundEvent(self, soundEvent):
        """Notifies (asynchronously) a sound event.
        
        Parameters
        ----------
        :param SoundEvent soundEVent:
            The sound event to notify.
        """
        with self._queue_lock:
            self._event_queue.append(soundEvent)
            self._queue_lock.notify_all()

    
