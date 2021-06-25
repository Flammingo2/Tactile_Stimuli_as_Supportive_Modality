# A block for the experiment.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 31.07.2018

import time
from trial import TrialState, Trial, generateTrials
import json
import os
from common import getTimeStamp, eprint, Action
import random
import csv
from page import Page, PageState

class Block:
    """Block of an experiment.
    """
    
    def __init__(self, experiment, session_result_folder, config):
        self.experiment = experiment
        # Block configuration
        self.config = {
            'block_id': "",
            'block_title': "block",
            'intro_gui': [],
            'summary_gui': [],
            'random_trials_order': True,
            'random_seed': None,
            'save_results': True,
            'save_results_summary': False,
            'trials': None,
            'trials_builder': None,
            'pages': None
            }
        if config is not None:
            for config_key in config:
                if config_key in self.config:
                    self.config[config_key] = config[config_key]
                else:
                    eprint("WARNING: Unknown block config entry: "+config_key)
        # Results
        self.result = {
            'start_trials_clock_time': -1,
            'stop_trials_clock_time': -1,
            'total_trials': -1,
            'total_trials_completed': -1,
            'correct_responses_count': 0,
            'wrong_responses_count': 0,
            'average_reaction_time': -1,
            'belt_vibration_intensity': -1
            }
        self.block_result_folder = None
        if self.config['save_results']:
            self.block_result_folder = (session_result_folder+"Block_"+
                                        self.config['block_id']+"/")
            if not os.path.exists(self.block_result_folder):
                os.makedirs(self.block_result_folder)
        # State of the block
        self.state = BlockState.NOT_STARTED
        self.active_trial_page_index = -1
        self.active_trial = None
        self.active_page = None
        # Trials (generate to test config, then clear)
        self.trials = []
        self.pages = []
        self.trials_pages = []
        self._loadTrialsPages()
        self.trials = []
        self.pages = []
        self.trials_pages = []
        
    
    def start(self):
        """Starts the block.
        """
        # Generates trials and pages from config
        self._loadTrialsPages()
        # Shows first trial or page
        self._startBlock()
    
    def update(self):
        """Check for updates.
        """
        if (self.state == BlockState.TRIALS_PAGES):
            if self.active_trial is not None:
                if self.active_trial.state == TrialState.NOT_STARTED:
                    self.active_trial.start()
                elif self.active_trial.state == TrialState.COMPLETED:
                    self._startNextTrialPage()
                    if self.active_trial_page_index == -1:
                        # Block completed
                        self._endBlock()
                else:
                    self.active_trial.update()
            elif self.active_page is not None:
                if self.active_page.state == PageState.INACTIVE:
                    self._startNextTrialPage()
                    if self.active_trial_page_index == -1:
                        # Block completed
                        self._endBlock()
                else:
                    self.active_page.update()
    
    def onAction(self, action):
        """ Handles an action.
        """
        if (self.state == BlockState.NOT_STARTED or
            self.state == BlockState.COMPLETED):
            # Ignore action
            return 
        if (action == Action.CANCEL or action == Action.QUIT):
            self._endBlock()
        elif (action == Action.RESTART):
            self._startBlock()
        elif self.active_page is not None:
            self.active_page.onAction(action)
        elif self.active_trial is not None:
            self.active_trial.onAction(action)
    
    def _startBlock(self):
        if not self.trials_pages:
            # No page or trials
            eprint("WARNING: Block without page or trial.")
            self.state = BlockState.COMPLETED
            return
        # Check current state
        if self.state == BlockState.TRIALS_PAGES:
            # Save partial results if any
            self._saveResults()
            # Cancel current page or trial
            self._cancelCurrentTrialPage()
        # Start first page or trial
        self.result['start_trials_clock_time'] = time.clock()
        self.state = BlockState.TRIALS_PAGES
        self.active_trial_page_index = -1
        self._startNextTrialPage()
        
    def _cancelCurrentTrialPage(self):
        """Cancels the current trial/page if any.
        """
        if self.active_page is not None:
            self.active_page.onAction(Action.CANCEL)
        if self.active_trial is not None:
            self.active_trial.onAction(Action.CANCEL)
        
    def _startNextTrialPage(self):
        """Increment the trial/page index and starts the next trial/page if any.
        """
        self.active_trial_page_index += 1
        self.active_page = None
        self.active_trial = None
        if (self.active_trial_page_index < 0 or
            self.active_trial_page_index >= len(self.trials_pages)):
            self.active_trial_page_index = -1
            return
        if isinstance(self.trials_pages[self.active_trial_page_index], 
                      Trial):
            self.active_trial = self.trials_pages[self.active_trial_page_index]
            self.active_trial.start()
        else:
            self.active_page = self.trials_pages[self.active_trial_page_index]
            self.active_page.start()
    
    def _endBlock(self):
        if self.state == BlockState.TRIALS_PAGES:
            # Save partial results if any
            self._saveResults()
            # Cancel current page or trial
            self._cancelCurrentTrialPage()
        if not self.trials or (self.trials[-1].state>=TrialState.SUMMARY):
            # No trial at all, or all trials completed
            self.state = BlockState.COMPLETED
        else:
            self.state = BlockState.NOT_STARTED
        # Clear trials and pages
        self.active_trial_page_index = -1
        self.active_trial = None
        self.active_page = None
        self.trials = []
        self.pages = []
        self.trials_pages = []
        
    def _loadTrialsPages(self):
        if self.config['random_seed'] is not None:
            random.seed(self.config['random_seed'])
        # Complete trials
        if (self.config['trials'] is not None):
            for trial_config in self.config['trials']:
                trial = Trial(
                    self.experiment,
                    self.block_result_folder,
                    trial_config
                    )
                self.trials.append(trial)
        # Trial builder
        if (self.config['trials_builder'] is not None):
            self.trials += generateTrials(self.experiment,
                                          self.block_result_folder,
                                          self.config['trials_builder'])
        # Shuffle trials
        if self.config['random_trials_order']:
            random.shuffle(self.trials)
        # Set position
        for i in range(len(self.trials)):
            self.trials[i].config['position'] = i
        # Pages
        if (self.config['pages'] is not None):
            for page_config in self.config['pages']:
                page = Page(self.experiment,
                                  page_config)
                self.pages.append(page)
        # Sequence of trials and pages
        self.trials_pages.extend(self.trials)
        for page in self.pages:
            for pos in page.config['after_trials']:
                if isinstance(pos, list):
                    # Page at regular interval
                    for pos2 in range(pos[0], pos[1]+1, pos[2]):
                        count_trial = 0
                        for i in range(len(self.trials_pages)):
                            if isinstance(self.trials_pages[i], Trial):
                                count_trial += 1
                            if count_trial > pos2:
                                # Insert before trial
                                self.trials_pages.insert(i, page)
                                break
                        if pos2 == len(self.trials) or pos2 == -1:
                            self.trials_pages.append(page)
                elif pos >= len(self.trials) or pos == -1:
                    # Page at the end
                    self.trials_pages.append(page)
                else:
                    # Page at the beginning or within trials
                    count_trial = 0
                    for i in range(len(self.trials_pages)):
                        if isinstance(self.trials_pages[i], Trial):
                            count_trial += 1
                        if count_trial > pos:
                            # Insert before trial
                            self.trials_pages.insert(i, page)
                            break
        # Insert intro and summary as pages
        if self.config['intro_gui']:
            self.trials_pages.insert(0, Page(
                self.experiment,
                {'page_id': "intro",
                 'after_trials': [0],
                 'page_timeout': -1,
                 'page_gui': self.config['intro_gui']}))
        if self.config['summary_gui']:
            self.trials_pages.append(Page(
                self.experiment,
                {'page_id': "summary",
                 'after_trials': [-1],
                 'page_timeout': -1,
                 'page_gui': self.config['summary_gui']}))
    
    def _saveResults(self):
        # Check for save
        if len(self.trials) == 0:
            return
        if not self.config['save_results']:
            return
        # Check trial completion
        all_trials_completed = (self.trials[-1].state>=TrialState.SUMMARY)
        trials_completed_count = 0
        for trial in self.trials:
            if trial.state >= TrialState.SUMMARY:
                trials_completed_count += 1
        if trials_completed_count == 0:
            # No trial to save
            return
        # Compute block results
        self.result['stop_trials_clock_time'] = time.clock()
        if self.experiment.isBeltConnected():
            self.result['belt_vibration_intensity'] = (
            self.experiment.getVibrationIntensity())
        correct_responses_count = 0
        wrong_responses_count = 0
        sum_reaction_time = 0
        reaction_time_count = 0
        total_trial_completed = 0
        for trial in self.trials:
            if (trial.result['reaction_time'] >= 0):
                reaction_time_count += 1
                sum_reaction_time += trial.result['reaction_time']
                total_trial_completed += 1
            if (trial.result['is_response_correct'] == 0):
                wrong_responses_count += 1
            elif (trial.result['is_response_correct'] == 1):
                correct_responses_count += 1
                # Note: ignore -1, undefined result
        self.result['correct_responses_count'] = correct_responses_count
        self.result['wrong_responses_count'] = wrong_responses_count
        self.result['total_trials'] = len(self.trials)
        self.result['total_trials_completed'] = total_trial_completed
        if (reaction_time_count > 0):
            self.result['average_reaction_time'] = (
                sum_reaction_time/reaction_time_count)
        else:
            self.result['average_reaction_time'] = -1

        # Save block config
        time_stamp = getTimeStamp()
        block_config_filename = (self.block_result_folder+time_stamp+
                                 ("_Block_config.json" if
                                  all_trials_completed else 
                                  "_Block_config_NOT_COMPLETED.json"))
        with open(block_config_filename, 'w') as fp:
            json.dump(self.config, fp, indent=4, sort_keys=True)
        # Save block summary
        block_summary_filename = (self.block_result_folder+time_stamp+
                                 ("_Block_summary.csv" if
                                  all_trials_completed else 
                                  "_Block_summary_NOT_COMPLETED.csv"))
        with open(block_summary_filename, 'wb') as fp:
            writer = csv.writer(fp, delimiter = '\t')
            writer.writerow(['block_id', self.config['block_id']])
            for key, value in self.result.items():
                writer.writerow([key, value])
        # Save trials in CSV
        trial_fields = [
            'position',
            'trial_id',
            'correct_answer',
            'visual_stimulus_text',
            'visual_stimulus_color',
            'vibration_stimulus',
            'response_on_action',
            'response_on_sound_detected',
            'start_trial_clock_time',
            'stop_trial_clock_time',
            'start_stimulus_clock_time',
            'stimulus_start_time',
            'start_visual_stimulus_clock_time',
            'stop_visual_stimulus_clock_time',
            'start_vibration_stimulus_clock_time',
            'stop_vibration_stimulus_clock_time',
            'response_clock_time',
            'response_action',
            'response_action_clock_time',
            'response_sound_onset_clock_time',
            'reaction_time',
            'is_response_correct',
            'average_update_time',
            'max_update_time',
            'min_update_time'
            ]
        trial_results_filename = (self.block_result_folder+time_stamp+
                                 ("_Results_trials.csv" if
                                  all_trials_completed else 
                                  "_Results_trials_NOT_COMPLETED.csv"))
        with open(trial_results_filename, 'wb') as fw:
            writer = csv.DictWriter(fw, fieldnames=trial_fields,
                                    extrasaction='ignore', delimiter = '\t')
            writer.writeheader()
            for trial in self.trials:
                all_field = trial.config.copy()
                all_field.update(trial.result)
                writer.writerow(all_field)
        # save summary
        if self.config['save_results_summary']:
            for trial in self.trials:
                origin_block_nr = 9 + trial.config['word_list']*2
                if "tactile" in self.experiment.session.blocks[origin_block_nr].config['block_id']:
                    tactile = True
                else:
                    tactile = False

                self.experiment.results_summary.append(
                    {
                        'VP_Nr': None,
                        'position': trial.config['position'],
                        'day': None,
                        'block_name': self.config['block_id'],
                        'visual_stimulus_text': trial.config['visual_stimulus_text'],
                        'word_list': trial.config['word_list'],
                        'tactile': tactile,
                        'correct_answer': trial.config['correct_answer'],
                        'answer': trial.result['response_action'],
                        'accuracy': trial.result['is_response_correct'],
                        'reaction_time': trial.result['reaction_time']
                    }
                )

        
    def getActiveTrialValue(self, key):
        if (self.active_trial is None):
            return None
        if key in self.active_trial.config:
            return self.active_trial.config[key]
        if key in self.active_trial.result:
            return self.active_trial.result[key]
        return None
    
    def getAverageReactionTime(self, between_last_components=None):
        """Returns the average reaction time in seconds.
        Returns -1 if no trial has a reaction time.
        """
        trial_count = 0
        sum_reaction_time = 0
        if not between_last_components:
            for trial in self.trials:
                if (trial.state >= TrialState.SUMMARY and
                    trial.result['reaction_time'] > 0):
                    trial_count += 1
                    sum_reaction_time += trial.result['reaction_time']
        else:
            for page_trial_index in range(
                self.active_trial_page_index-1, 0, -1):
                if isinstance(self.trials_pages[page_trial_index], Page):
                    page = self.trials_pages[page_trial_index]
                    if between_last_components in page.config['page_gui']:
                        break
                else:
                    trial = self.trials_pages[page_trial_index]
                    if (trial.state >= TrialState.SUMMARY and
                        trial.result['reaction_time'] > 0):
                        trial_count += 1
                        sum_reaction_time += trial.result['reaction_time']
        if trial_count > 0:
            return sum_reaction_time/float(trial_count)
        return -1
    
    def getAccuracy(self, between_last_components=None):
        """Returns the accuracy in percent (in range [0-1]).
        Returns -1 if no trial has a response.
        """
        trial_count = 0
        sum_correct_response = 0
        if not between_last_components:
            for trial in self.trials:
                if (trial.state >= TrialState.SUMMARY and
                    trial.result['is_response_correct'] >= 0):
                    trial_count += 1
                    sum_correct_response += trial.result['is_response_correct']
        else:
            for page_trial_index in range(
                self.active_trial_page_index-1, 0, -1):
                if isinstance(self.trials_pages[page_trial_index], Page):
                    page = self.trials_pages[page_trial_index]
                    if between_last_components in page.config['page_gui']:
                        break
                else:
                    trial = self.trials_pages[page_trial_index]
                    if (trial.state >= TrialState.SUMMARY and
                        trial.result['is_response_correct'] >= 0):
                        trial_count += 1
                        sum_correct_response += trial.result['is_response_correct']
        if trial_count > 0:
            return sum_correct_response/float(trial_count)
        return -1

class BlockState:
    """Enumeration of block states."""
    NOT_STARTED = -1
    TRIALS_PAGES = 0
    COMPLETED = 1
    