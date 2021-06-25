# A page for the experiment.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 20.08.2018

from common import eprint, Action
import time

class Page:
    """Page with information for a block.
    """
    
    def __init__(self, experiment, config):
        self.experiment = experiment
        # State of the page
        self.state = PageState.INACTIVE
        # Configuration of the page
        self.config = {
            'page_id': "",
            'after_trials': [],
            'page_timeout': -1, # -1 no timeout
            'page_gui': []
            }
        if config is not None:
            for config_key in config:
                if config_key in self.config:
                    self.config[config_key] = config[config_key]
                else:
                    eprint("WARNING: Unknown page config entry: "+config_key)
        # Page variables
        self.start_page_clock_time = -1
        
    def start(self):
        if self.state == PageState.ACTIVE:
            eprint("WARNING: Start a page already active.")
            return
        self.start_page_clock_time = time.clock()
        self.experiment.showUIComponents(
            components=self.config['page_gui'])
        self.state = PageState.ACTIVE
        
    def stop(self):
        if self.state == PageState.INACTIVE:
            eprint("WARNING: Stop a page already inactive.")
            return
        self.start_page_clock_time = -1
        self.experiment.clearUIComponents(
            components=self.config['page_gui'])
        self.state = PageState.INACTIVE
        
    def get_remaining_page_time(self):
        """Returns the remaining time until timeout, or -1 if no timeout or the 
        page is inactive.
        """
        if (self.state == PageState.ACTIVE and
            self.config['page_timeout'] > 0):
            remaining = (float(self.config['page_timeout'])-
                         (time.clock()-self.start_page_clock_time))
            if remaining > 0:
                return remaining
            else:
                return 0
        return -1
        
    def update(self):
        # Check page timeout
        if (self.state == PageState.ACTIVE and
            self.config['page_timeout'] is not None and
            self.config['page_timeout'] > 0):
            if self.get_remaining_page_time() <= 0:
                # Page timeout
                self.stop()
        
    def onAction(self, action):
        if self.state == PageState.INACTIVE:
            eprint("WARNING: Action received on inactive page.")
            return
        if (action == Action.NEXT or
            action == Action.PREVIOUS or
            action == Action.CANCEL or
            action == Action.QUIT):
            self.stop()
        elif (action == Action.RESTART):
            # Reset page
            self.stop()
            self.start()
        
class PageState:
    """Enumeration of page states. """
    INACTIVE = 0
    ACTIVE = 1