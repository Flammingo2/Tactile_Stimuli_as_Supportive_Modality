# Common classes and values for experiment.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 31.07.2018

from __future__ import print_function
import time
import sys

class Action:
    """Enumeration of actions from the GUI.
    """
    NEXT = "next"
    PREVIOUS = "previous"
    CANCEL = "cancel"
    QUIT = "quit"
    RESTART = "restart"
    LOAD_SESSION = "load session"
    TOGGLE_FULLSCREEN = "toggle fullscreen"
    CONNECT_BELT = "connect belt"
    TEST_VIBRATION = "test vibration"
    VIBRATION_BLUE = "vibration blue"
    VIBRATION_GREEN = "vibration green"
    VIBRATION_RED = "vibration red"
    VIBRATION_YELLOW = "vibration yellow"
    RESPONSE_BLUE = "BLUE"
    RESPONSE_GREEN = "GREEN"
    RESPONSE_RED = "RED"
    RESPONSE_YELLOW = "YELLOW"
    CLEAR_CLICK_COUNT = "clear click count"
    
class Symbol:
    """Enumeration of symbols used as stimulus in the different modalities.
    """
    BLUE = "BLUE"
    GREEN = "GREEN"
    RED = "RED"
    YELLOW = "YELLOW"
    WHITE = "WHITE"

class Language:
    ENGLISH = "en"
    GERMAN = "de"

def getTimeStamp():
    """Returns a time stamp of the current time.
    """
    return time.strftime("%Y-%m-%d_T%H%M%S")

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
    