# Class for generating beeps.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 31.07.2018

from psychopy.sound.backend_pyo import SoundPyo

class BeepManager(object):
    """
    The beep manager is responsible for generating beeps.
    
    Required module
    ---------------
    This module requires psychoPy (http://www.psychopy.org) and Pyo 
    (http://ajaxsoundstudio.com/software/pyo/).
    
    """

    def __init__(self, default_frequency='C', default_duration=0.1):
        """
        Constructor.
        
        Parameters
        ----------
        :param int default_frequency:
            The frequency for the default beep. This can be a note or a 
            frequency in Hz.
        :param int default_duration:
            The duration for the default beep in seconds.
        """
        self._beep_default_frequency = default_frequency
        self._beep_default_duration = default_duration
        self._default_beep = SoundPyo(value=default_frequency, 
                                      secs=default_duration,
                                      autoLog=True)
        
    def beep(self):
        """
        Plays the default beep.
        """
        self._default_beep.play(log=False)
        
    def setBeep(self, default_frequency='C', default_duration=0.1):
        """
        Sets the parameters of the default beep.
        """
        self._default_beep = SoundPyo(value=default_frequency, 
                                      secs=default_duration,
                                      autoLog=True)
        
        