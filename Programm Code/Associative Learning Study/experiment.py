# -*- coding: utf-8 -*-
#!/usr/bin/env python

# Module with the components of the experiment.

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the
# prior explicit written consent of the copyright owner.

# Last update: 31.07.2018

import threading
import random
from audiocapture import SoundRecorder
from pybelt.classicbelt import BeltController, BeltMode
import pygame
import json
from pygame.constants import FULLSCREEN
import os
import sys
import trial
from session import Session, SessionState
from common import Action, eprint, Symbol, Language, getTimeStamp
from block import BlockState
from pygame.rect import Rect
from glyph.glyph import Glyph, Macros
import time
from builtins import bytes
from scipy.linalg.tests.test_fblas import accuracy
import tkinter
from tkinter import filedialog
import csv


RESOURCES_FOLDER = "./session_data/"
DEFAULT_SESSION_FILE_T = "./session_data/session_t.json"
DEFAULT_SESSION_FILE_C = "./session_data/session_c.json"
RESULT_FOLDER = "./results/"
TOUCHSCREEN_MODE = True

class Experiment(threading.Thread):
    """Experiment.
    """

    def __init__(self, session_file="", mapping_file=""):
        threading.Thread.__init__(self)
        # Sound recorder settings
        self.audio_recorder = SoundRecorder(
            handler=None,
            threshold_level_onset=800,
            threshold_level_offset=100)
        # Belt
        self.belt_controller = BeltController(delegate=self)
        # Session
        self.session_file = session_file
        self.mapping_file = mapping_file
        self.session_result_folder = RESULT_FOLDER
        self.session = None
        self.session_info = None
        # UI
        self.redraw = True
        self.stop_flag = False
        self.active_components = []
        self.active_buttons = []
        self.stored_surfaces_glyphs = {}
        self.cursor_visible = True
        self.is_fullscreen = False
        # Default strings
        self.strings = {
            'en': {
                'BLUE':                         u"BLUE",
                'GREEN':                        u"GREEN",
                'RED':                          u"RED",
                'YELLOW':                       u"YELLOW",
                'connect_button_label':         "Connect belt",
                'quit_button_label':            "Quit",
                'completed_block_label':        "Completed",
                'finish_button_label':          "Finish",
                'correct_answer_label':         "Correct answer: ",
                'reaction_time_ms_label':       "Reaction time: ",
                'accuracy_label':               "Accuracy: ",
                'correct_response_label':       "Correct",
                'wrong_response_label':         "Wrong",
                'start_experiment_button_label': "Start experiment",
                'quit_experiment_button_label': "Quit",
                'start_block_button_label':     "Start",
                'test_belt_button_label':       "Test belt",
                'back_to_menu_button_label':    "Back to menu",
                'next_button_label':            "Next",
                'retry_button_label':           "Retry",
                'toggle_fullscreen_button_label': "Fullscreen",
                'pause_instructions':           "Pause",
                'continue_button_label':        "Continue",
                'continue_trial_instructions':  "Press 'continue'"
                },
            'de': {
                'BLUE':                         u"BLAU",
                'GREEN':                        u"GRÜN",
                'RED':                          u"ROT",
                'YELLOW':                       u"GELB"
                }
            }
        # Default values
        self.values = {
            'screen_resolution_x':              800,
            'screen_resolution_y':              600,
            'visual_stimulus_font':             "arial",
            'visual_stimulus_font_size':        20,
            'visual_stimulus_font_bold':        1,
            'instruction_font':                 "arial",
            'instruction_font_size':            18,
            'instruction_font_bold':            0,
            'title_font':                       "arial",
            'title_font_size':                  22,
            'title_font_bold':                  1,
            'button_font':                      "arial",
            'button_font_size':                 20,
            'button_font_bold':                 0,
            'vibromotor_index_blue':            7,
            'vibromotor_index_green':           8,
            'vibromotor_index_red':             10,
            'vibromotor_index_yellow':          5,
            'gamepad_index_blue':				6,
	        'gamepad_index_green':				1,
	        'gamepad_index_red':				2,
	        'gamepad_index_yellow':				3,
            'padding_x_ui':                     10,
            'padding_y_ui':                     5,
            'screen_padding_x_ui':              20,
            'screen_padding_y_ui':              20,
            'margin_x_ui':                      5,
            'margin_y_ui':                      5,
            'screen_padding_x':                 20,
            'screen_padding_y':                 0,
            'color_background':                 "#000000",
            'color_instructions':               "#ffffff",
            'color_instructions_warning':       "#ff0000",
            'color_button_foreground':          "#000000",
            'color_button_disabled_foreground': "#000000",
            'color_button_background':          "#e6e6e6",
            'color_button_disabled_background': "#8e8fa5",
            'color_button_decoration':          "#424242",
            'color_button_disabled_decoration': "#1c1c1c",
            'color_button_width':               100,
            'color_button_height':              100,
            'button_corner_size':               5,
            'button_corner_border_size':        2,
            'color_button_corner':              "#6e6e6e",
            'color_button_disabled_corner':     "#ffffff",
            'color_blue':                       "#0000ff",
            'color_green':                      "#00ff00",
            'color_red':                        "#ff0000",
            'color_yellow':                     "#ffff00",
            'color_white':                      "#ffffff",
            'color_go_button_foreground':       "#254820",
            'color_go_button_background':       "#caf0c5",
            'color_go_button_decoration':       "#3a931f",
            'color_warning_button_foreground':  "#533214",
            'color_warning_button_background':  "#efccac",
            'color_warning_button_decoration':  "#c05e21",
            'fixation_cross_color':             "#ffffff",
            'rectangle_stimulus_width':         100,
            'rectangle_stimulus_height':        100,
            'mic_image_file':                   "mic.png",
            'button_image_file':                "press_button.png",
            'logo_image_file':                  "logo.png",
            'better_icon_image_file':           "better_icon.png",
            'worse_icon_image_file':            "worse_icon.png",
            'similar_icon_image_file':          "similar_icon.png",
            'audio_threshold_level_onset':      150,
            'audio_threshold_level_offset':     100,
            'audio_window_onset':               25,
            'audio_window_offset':              25,
            'minimum_audio_response_duration':  0.100,
            'minimum_touch_and_feel_clicks':    5,
            'color_square_highlight_border':    "#ffffff",
            'touch_screen_mode':                True
            }
        self.results_summary = []
        self.words = []
        self.messages = ["Wundervoll :)", "Super :)", "Sehr gut :)"]
        # Images
        self.images = {
            'mic': ('mic_image_file', None),
            'button': ('button_image_file', None),
            'logo': ('logo_image_file', None),
            'better_icon': ('better_icon_image_file', None),
            'worse_icon': ('worse_icon_image_file', None),
            'similar_icon': ('similar_icon_image_file', None)
            }
        # Fonts
        self.font_instruction = None
        self.font_instruction_bold = None
        self.font_visual_stimulus = None
        self.font_button = None
        self.font_title = None
        # Window area
        self.drawing_rect = None
        self.title_rect = None
        self.description_rect = None
        self.command_rect = None
        # Click count for touch and feel
        self.click_count = None

    def connectBelt(self):
        pygame.mouse.set_cursor(*pygame.cursors.diamond)
        if self.belt_controller.getBeltMode() == BeltMode.UNKNOWN:
            # Connect
            try:
                self.belt_controller.connectBeltSerial()
            except:
                eprint("WARNING: The belt cannot be connected.")
        else:
            eprint("WARNING: A belt is already connected.")
        if self.cursor_visible:
            pygame.mouse.set_cursor(
                *pygame.cursors.arrow)
        else:
            pygame.mouse.set_cursor(
                (8,8), (0,0), (0,0,0,0,0,0,0,0), (0,0,0,0,0,0,0,0))
        # Redraw after connection event
        self.redraw = True

    def testVibration(self):
        if not self.isBeltConnected():
            return
        pygame.mouse.set_cursor(*pygame.cursors.diamond)
        if self.belt_controller.getBeltMode() != BeltMode.APP_MODE:
            self.belt_controller.switchToMode(BeltMode.APP_MODE)
        # Vibrate 1 second for each color
        self.startVibrationStimulus(Symbol.BLUE)
        time.sleep(0.5)
        self.stopVibrationStimulus()
        self.startVibrationStimulus(Symbol.GREEN)
        time.sleep(0.5)
        self.stopVibrationStimulus()
        self.startVibrationStimulus(Symbol.RED)
        time.sleep(0.5)
        self.stopVibrationStimulus()
        self.startVibrationStimulus(Symbol.YELLOW)
        time.sleep(0.5)
        self.stopVibrationStimulus()
        if self.cursor_visible:
            pygame.mouse.set_cursor(
                *pygame.cursors.arrow)
        else:
            pygame.mouse.set_cursor(
                (8,8), (0,0), (0,0,0,0,0,0,0,0), (0,0,0,0,0,0,0,0))
        # Redraw after connection event
        self.redraw = True

    def isBeltConnected(self):
        return self.belt_controller.getBeltMode() != BeltMode.UNKNOWN

    def getVibrationIntensity(self):
        if self.isBeltConnected():
            return self.belt_controller._default_vibration_intensity
        else:
            -1

    def testVibrationStimulus(self, stimulus):
        if self.belt_controller.getBeltMode() == BeltMode.UNKNOWN:
            eprint("WARNING: No belt connected.")
            return
        if (stimulus == 'BLUE'):
            position = int(self.values['vibromotor_index_blue'])
            packet = bytes([0x8A,
                            0x91,
                            position, # Position L
                            0x00,
                            0x64, # Intensity
                            0x01, # Iterations
                            0xF4, # Duration L
                            0x01, # Duration H
                            0xF4, # Period L
                            0x01, # Period H
                            0x00,
                            0x0A])
            self.belt_controller._socket.send(packet)
            ## 60ms ->  \x3C
            ## 100ms -> \x64
            ## 200ms -> \xC8
            ## 250ms -> \xFA
            ## 500ms -> \xF4\x01
            ##                                                        v I v D     v P
            self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x01\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'GREEN'):
            position = int(self.values['vibromotor_index_green'])
            packet = bytes([0x8A,
                            0x91,
                            position, # Position L
                            0x00,
                            0x64, # Intensity
                            0x01, # Iterations
                            0xF4, # Duration L
                            0x01, # Duration H
                            0xF4, # Period L
                            0x01, # Period H
                            0x00,
                            0x0A])
            self.belt_controller._socket.send(packet)
            ##                                                        v I v D     v P
            self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x02\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'RED'):
            position = int(self.values['vibromotor_index_red'])
            packet = bytes([0x8A,
                            0x91,
                            position, # Position L
                            0x00,
                            0x64, # Intensity
                            0x01, # Iterations
                            0xF4, # Duration L
                            0x01, # Duration H
                            0xF4, # Period L
                            0x01, # Period H
                            0x00,
                            0x0A])
            self.belt_controller._socket.send(packet)
            ##                                                        v I v D     v P
            self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x03\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'YELLOW'):
            position = int(self.values['vibromotor_index_yellow'])
            packet = bytes([0x8A,
                            0x91,
                            position, # Position L
                            0x00,
                            0x64, # Intensity
                            0x01, # Iterations
                            0xF4, # Duration L
                            0x01, # Duration H
                            0xF4, # Period L
                            0x01, # Period H
                            0x00,
                            0x0A])
            self.belt_controller._socket.send(packet)
            ##                                                        v I v D     v P
            self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x04\x64\x00\xFA\x00\x00\x0A')
        else:
            eprint("WARNING: Unknown vibration stimulus.")

    def startVibrationStimulus(self, stimulus):
        if self.belt_controller.getBeltMode() == BeltMode.UNKNOWN:
            eprint("WARNING: No belt connected.")
            return
        if (stimulus == 'BLUE'):
            self.belt_controller.vibrateAtPositions(
                [self.values['vibromotor_index_blue']], 0)
            ## 60ms ->  \x3C
            ## 100ms -> \x64
            ## 200ms -> \xC8
            ## 250ms -> \xFA
            ## 500ms -> \xF4\x01
            ##                                                        v I v D     v P
            # self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x01\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'GREEN'):
            self.belt_controller.vibrateAtPositions(
                [self.values['vibromotor_index_green']], 0)
            ##                                                        v I v D     v P
            # self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x02\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'RED'):
            self.belt_controller.vibrateAtPositions(
                [self.values['vibromotor_index_red']], 0)
            ##                                                        v I v D     v P
            # self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x03\x64\x00\xFA\x00\x00\x0A')
        elif (stimulus == 'YELLOW'):
            self.belt_controller.vibrateAtPositions(
                [self.values['vibromotor_index_yellow']], 0)
            ##                                                        v I v D     v P
            # self.belt_controller._socket.send(b'\x8A\x91\x00\x00\x64\x04\x64\x00\xFA\x00\x00\x0A')
        else:
            eprint("WARNING: Unknown vibration stimulus.")

    def stopVibrationStimulus(self):
        if self.belt_controller.getBeltMode() == BeltMode.UNKNOWN:
            eprint("WARNING: No belt connected.")
            return
        self.belt_controller.stopVibration()

    def showUIComponents(self, components):
        if components is None:
            return
        if isinstance(components, (str, unicode)):
            if len(components) > 0:
                self.active_components.append(components)
        else:
            self.active_components += components
        self.redraw = True

    def clearUIComponents(self, components):
        if components is None:
            return
        if isinstance(components, (str, unicode)):
            if components in self.active_components:
                self.active_components.remove(components)
            else:
                eprint("WARNING: Try to remove nonexistent UI component: "+
                       str(components))
        else:
            for component in components:
                if component in self.active_components:
                    self.active_components.remove(component)
                else:
                    eprint("WARNING: Try to remove nonexistent UI component: "+
                           str(component))
        self.redraw = True

    def clearAllUIComponents(self):
        self.active_components = []
        self.redraw = True

    def toggleFullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode(
                (self.values['screen_resolution_x'],
                 self.values['screen_resolution_y']), FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(
                (self.values['screen_resolution_x'],
                 self.values['screen_resolution_y']))
        self.redraw = True
        
    def run(self):
        print("INFO: Start experiment.")
        print("INFO: Load strings and values and mapping.")
        self.load_strings(RESOURCES_FOLDER+"strings.json")
        self.load_values(RESOURCES_FOLDER+"values.json")
        self.load_mapping()
        print("INFO: Initialize sound recorder.")
        self.audio_recorder._threshold_level_onset = (
            self.values['audio_threshold_level_onset'])
        self.audio_recorder._threshold_level_offset = (
            self.values['audio_threshold_level_offset'])
        self.audio_recorder._onset_window = (
            self.values['audio_window_onset'])
        self.audio_recorder._offset_window = (
            self.values['audio_window_offset'])
        self.audio_recorder.initRecorder()
        print("INFO: Load session.")
        self.loadSession()
        print("INFO: Init pygame.")
        pygame.init()
        self.load_images(RESOURCES_FOLDER)
        self.load_fonts()
        if self.is_fullscreen:
            self.screen = pygame.display.set_mode(
                (self.values['screen_resolution_x'],
                 self.values['screen_resolution_y']), FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(
                (self.values['screen_resolution_x'],
                 self.values['screen_resolution_y']))
        # Window area
        self.drawing_rect = Rect(
            self.values['screen_padding_x'],
            self.values['screen_padding_y'],
            (self.values['screen_resolution_x']-
             self.values['screen_padding_x']*2),
            (self.values['screen_resolution_y']-
             self.values['screen_padding_y']*2)
            )
        self.title_rect = Rect(
            self.drawing_rect.x,
            self.drawing_rect.y,
            self.drawing_rect.width,
            self.drawing_rect.height/5
            )
        self.description_rect = Rect(
            self.drawing_rect.x,
            self.drawing_rect.height/5+self.values['margin_y_ui'],
            self.drawing_rect.width,
            self.drawing_rect.height/5*3-self.values['margin_y_ui']*2+20
            )
        self.description_top_rect = Rect(
            self.description_rect.x,
            self.description_rect.y,
            self.description_rect.width,
            self.description_rect.height/2
            )
        self.description_bottom_rect = Rect(
            self.description_rect.x,
            self.description_rect.y+self.description_rect.height/2,
            self.description_rect.width,
            self.description_rect.height/2
            )
        self.description_left_rect = Rect(
            self.description_rect.x,
            self.description_rect.y,
            self.description_rect.width/2,
            self.description_rect.height
            )
        self.description_right_rect = Rect(
            self.description_rect.x+self.description_rect.width/2,
            self.description_rect.y,
            self.description_rect.width/2,
            self.description_rect.height
            )
        self.command_rect = Rect(
            self.drawing_rect.x,
            self.drawing_rect.height/5*4,
            self.drawing_rect.width/5*4,
            self.drawing_rect.height/5
            )
    
        print("INFO: Start event and update loop.")
        self.stop_flag = False
        while not self.stop_flag:
            # Events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    if self.session is not None:
                        self.session.onAction(Action.QUIT)
                    self.stop_flag = True
                elif (event.type == pygame.KEYDOWN and
                    event.key == pygame.K_ESCAPE):
                    # Exit full screen
                    self.screen = pygame.display.set_mode(
                        (self.values['screen_resolution_x'],
                         self.values['screen_resolution_y']))
                    self.redraw = True
                elif (event.type == pygame.KEYDOWN and
                    event.key == pygame.K_f):
                    # Full screen
                    self.screen = pygame.display.set_mode(
                        (self.values['screen_resolution_x'],
                         self.values['screen_resolution_y']), FULLSCREEN)
                    self.redraw = True
                elif (event.type == pygame.KEYDOWN and
                      (event.key == pygame.K_c)):
                    # Toggle mouse
                    if self.cursor_visible:
                        pygame.mouse.set_cursor((8,8),(0,0),
                                                (0,0,0,0,0,0,0,0),
                                                (0,0,0,0,0,0,0,0))
                    else:
                        pygame.mouse.set_cursor(*pygame.cursors.arrow)
                    self.cursor_visible = not self.cursor_visible
                elif (event.type == pygame.KEYDOWN and
                      (event.key == pygame.K_SPACE or
                       event.key == pygame.K_RETURN)):
                    if self.session is not None:
                        self.session.onAction(Action.NEXT)
                elif (event.type == pygame.KEYDOWN and
                      (event.key == pygame.K_q or
                       event.key == pygame.K_BACKSPACE)):
                    if self.session is not None:
                        self.session.onAction(Action.CANCEL)
                elif (event.type == pygame.KEYDOWN and 
                      (event.key == pygame.K_6)):
                    if self.session is not None:
                        self.session.onAction(Action.RESPONSE_GREEN)
                elif (event.type == pygame.KEYDOWN and 
                      (event.key == pygame.K_5)):
                    if self.session is not None:
                        self.session.onAction(Action.RESPONSE_RED)
                elif (event.type == pygame.KEYDOWN and 
                      (event.key == pygame.K_8)):
                    if self.session is not None:
                        self.session.onAction(Action.RESPONSE_YELLOW)
                elif (event.type == pygame.KEYDOWN and 
                      (event.key == pygame.K_7)):
                    if self.session is not None:
                        self.session.onAction(Action.RESPONSE_BLUE)
                elif (event.type == pygame.MOUSEBUTTONUP and
                      event.button == 1):
                    # Mouse click -> Check active buttons
                    for button in self.active_buttons:
                        if button[1].collidepoint(
                            pygame.mouse.get_pos()):
                            # Check direct action
                            if button[0] == Action.QUIT:
                                if self.session is not None:
                                    self.session.onAction(Action.QUIT)
                                self.stop_flag = True
                            elif button[0] == Action.CONNECT_BELT:
                                self.connectBelt()
                            elif button[0] == Action.TEST_VIBRATION:
                                self.testVibration()
                            elif button[0] == Action.TOGGLE_FULLSCREEN:
                                self.toggleFullscreen()
                            elif button[0] == Action.LOAD_SESSION:
                                self.loadSession()
                            elif button[0] == Action.CLEAR_CLICK_COUNT:
                                self.click_count = None
                            # Send action to session
                            elif self.session is not None:
                                self.session.onAction(button[0])
                    for button in self.active_buttons:
                        if (button[0] == Action.VIBRATION_BLUE or
                            button[0] == Action.VIBRATION_GREEN or
                            button[0] == Action.VIBRATION_RED or
                            button[0] == Action.VIBRATION_YELLOW):
                            # Note: Stop vibration even when mouse is not on
                            # button to manage mouse position that exists button
                            # between mouse-down and mouse-up.
                            if not self.values['touch_screen_mode']:
                                self.stopVibrationStimulus()
                            break
                elif (event.type == pygame.MOUSEBUTTONDOWN and
                      event.button == 1):
                    for button in self.active_buttons:
                        vibration_symbol = None
                        if (button[0] == Action.VIBRATION_BLUE and
                            button[1].collidepoint(pygame.mouse.get_pos())):
                            vibration_symbol = Symbol.BLUE
                        if (button[0] == Action.VIBRATION_GREEN and
                            button[1].collidepoint(pygame.mouse.get_pos())):
                            vibration_symbol = Symbol.GREEN
                        if (button[0] == Action.VIBRATION_RED and
                            button[1].collidepoint(pygame.mouse.get_pos())):
                            vibration_symbol = Symbol.RED
                        if (button[0] == Action.VIBRATION_YELLOW and
                            button[1].collidepoint(pygame.mouse.get_pos())):
                            vibration_symbol = Symbol.YELLOW
                        if vibration_symbol is not None:
                            if self.values['touch_screen_mode']:
                                self.testVibrationStimulus(vibration_symbol)
                            else:
                                self.startVibrationStimulus(vibration_symbol)
                            # Click count
                            if self.click_count is None:
                                self.click_count = {
                                    Symbol.BLUE: 0,
                                    Symbol.GREEN: 0,
                                    Symbol.RED: 0,
                                    Symbol.YELLOW: 0
                                    }
                            self.click_count[vibration_symbol] += 1
                            self.redraw = True
                elif (event.type == pygame.JOYBUTTONDOWN):
                    gamepad_action = None
                    if event.button == self.values['gamepad_index_blue']:
                        gamepad_action = Action.RESPONSE_BLUE
                    elif event.button == self.values['gamepad_index_green']:
                        gamepad_action = Action.RESPONSE_GREEN
                    elif event.button == self.values['gamepad_index_red']:
                        gamepad_action = Action.RESPONSE_RED
                    elif event.button == self.values['gamepad_index_yellow']:
                        gamepad_action = Action.RESPONSE_YELLOW

                    if self.session is not None:
                        self.session.onAction(gamepad_action)

            # Experiment update
            if self.session is not None:
                self.session.update()
            # Display UI
            if self.redraw and not self.stop_flag:
                self.redraw = False
                self.drawUI()

        self._saveMapping()
        self._saveSessionFile()
        self._saveResultsSummary()
        print("INFO: Disconnect belt.")
        self.belt_controller.disconnectBelt()
        print("INFO: End of the experiment.")

    def drawUI(self):
        self.active_buttons = []
        if self.isBeltConnected():
            self.screen.fill((0, 0, 0))
        else:
            self.screen.fill(pygame.Color("#240200"))
        for component in self.active_components:
            self._draw_component(component)
        pygame.display.flip()

    def load_strings(self, string_file):
        """Loads the strings from a JSON file.
        """
        if string_file:
            if os.path.isfile(string_file):
                with open(string_file, 'r') as fp:
                    strings_data = json.load(fp)
                    for lang_key in strings_data:
                        if lang_key in self.strings:
                            # Update language
                            self.strings[lang_key].update(
                                    strings_data[lang_key])
                        else:
                            # Add language
                            self.strings[lang_key] = strings_data[lang_key]

    def getString(self, key):
        """Returns a localized string.
        """
        lang = "en"
        if (key in self.words):
            return key
        elif not key in self.strings[lang]:
            eprint("ERROR: Unknown string key: "+str(key))
            return ""
        localized_string = self.strings[lang][key]
        if self.session is not None:
            if 'language' in self.session.config:
                lang = self.session.config['language']
                if lang in self.strings:
                    if key in self.strings[lang]:
                        localized_string = self.strings[lang][key]
        return localized_string

    def getColor(self, color_key):
        if color_key in self.values:
            return pygame.Color(self.values[color_key])
        elif color_key == Symbol.BLUE:
            return pygame.Color(self.values['color_blue'])
        elif color_key == Symbol.GREEN:
            return pygame.Color(self.values['color_green'])
        elif color_key == Symbol.RED:
            return pygame.Color(self.values['color_red'])
        elif color_key == Symbol.YELLOW:
            return pygame.Color(self.values['color_yellow'])
        elif color_key == Symbol.WHITE:
            return pygame.Color(self.values['color_white'])
        else:
            return None

    def load_values(self, values_file):
        """Loads the values from a JSON file.
        """
        if values_file:
            if os.path.isfile(values_file):
                with open(values_file, 'r') as fp:
                    values_data = json.load(fp)
                    self.values.update(values_data)

    def load_words(self, words_file):
        """Loads the words from a JSON file.
        """
        if words_file:
            if os.path.isfile(words_file):
                with open(words_file, 'r') as fp:
                    self.words = json.load(fp)

    def _createRandomMapping(self):
        """Creates random mapping of words and colors.
        """
        self.load_words(RESOURCES_FOLDER+"words.json")
        random.shuffle(self.words)
        one_forth = len(self.words)/4
        
        # assign colors 
        color_template = ["RED"]*5 + ["BLUE"]*5 + ["GREEN"]*5 + ["YELLOW"]*5
        words = []
        for i in range(len(self.words)):
            if i % one_forth == 0:
                random.shuffle(color_template)
            words.append([self.words[i], color_template[i%one_forth]])

        # divide words into four lists
        self.words = [words[:one_forth], words[one_forth:one_forth*2], words[one_forth*2:one_forth*3], words[one_forth*3:]]

    def load_mapping(self):
        if self.mapping_file:
            try :
                with open(self.mapping_file, 'r') as fp:
                    self.words = json.load(fp)
            except Exception as e:
                eprint("ERROR: Mapping file invalid.")
                eprint(str(e))
                return
        else:
            self._createRandomMapping()



    def load_images(self, resources_folder):
        """Loads all images.
        """
        for img_key in self.images:
            img_file_key = self.images[img_key][0]
            img_file = resources_folder+self.values[img_file_key]
            if os.path.isfile(img_file):
                self.images[img_key] = (img_file_key,
                                        pygame.image.load(img_file))
            else:
                eprint("WARNING: Image file not found.")

    def load_fonts(self):
        """Loads the fonts for pygame and macros for Glyph.
        """
        self.font_visual_stimulus = pygame.font.SysFont(
            self.values['visual_stimulus_font'],
            self.values['visual_stimulus_font_size'],
            self.values['visual_stimulus_font_bold'])
        self.font_instruction = pygame.font.SysFont(
            self.values['instruction_font'],
            self.values['instruction_font_size'],
            self.values['instruction_font_bold'])
        self.font_instruction_bold = pygame.font.SysFont(
            self.values['instruction_font'],
            self.values['instruction_font_size'],
            1)
        self.font_button = pygame.font.SysFont(
            self.values['button_font'],
            self.values['button_font_size'],
            self.values['button_font_bold'])
        self.font_title = pygame.font.SysFont(
            self.values['title_font'],
            self.values['title_font_size'],
            self.values['title_font_bold'])
        Macros['b'] = ('font', self.font_instruction_bold)
        Macros['blue'] = ('color', self.getColor('color_blue'))
        Macros['green'] = ('color', self.getColor('color_green'))
        Macros['red'] = ('color', self.getColor('color_red'))
        Macros['yellow'] = ('color', self.getColor('color_yellow'))

    def loadSession(self):
        """Loads or reloads the session.
        """
        print("INFO: Load session.")
        if (self.session is not None and
            self.session.state != SessionState.NOT_STARTED):
            # Cancel session
            eprint("WARNING: Cancel session.")
            self.session.onAction(Action.QUIT)
        # Check session parameters
        if not self.session_file:
            self.session_file = random.choice([DEFAULT_SESSION_FILE_C, DEFAULT_SESSION_FILE_T])
        if not os.path.isfile(self.session_file):
            eprint("ERROR: Session file not found.")
            return
        session_config = None
        try :
            with open(self.session_file, 'r') as fp:
                session_config = json.load(fp)
        except Exception as e:
            eprint("ERROR: Session file invalid.")
            eprint(str(e))
            return
        self.session_info = session_config
        if session_config['language'] not in self.strings:
            eprint("ERROR: Unknown language code.")
            return
        if not self.session_result_folder:
            self.session_result_folder = "./"
        if not os.path.exists(self.session_result_folder):
            try:
                os.makedirs(self.session_result_folder)
            except:
                eprint("ERROR: Unable to create result folder.")
                return
        # Create session
        self.session = Session(self, self.session_result_folder,
                                     session_config)
        # Clear session config screen
        self.clearAllUIComponents()
        # Start session
        self.session.start()

    def getImage(self, image_key):
        if image_key in self.images:
            return self.images[image_key][1]
        else:
            return None

    def _saveMapping(self):
        if self.words:
            with open(self.session.session_result_folder+'mapping.json', 'w') as fp:
                json.dump(self.words, fp, indent=4)

    def _saveSessionFile(self):
        if self.session_file:
            with open(self.session.session_result_folder+'session.json', 'w') as fp:
                json.dump(self.session_info, fp, indent=4)

    def _saveResultsSummary(self):
        time_stamp = getTimeStamp()
        trial_fields = [
            'VP_Nr',
            'position',
            'day',
            'block_name',
            'visual_stimulus_text',
            'word_list',
            'tactile',
            'correct_answer',
            'answer',
            'accuracy',
            'reaction_time'
        ]
        results_summary_filename = self.session.session_result_folder+time_stamp+"_results_summary.csv"
        with open(results_summary_filename, 'wb') as fw:
            writer = csv.DictWriter(fw, fieldnames=trial_fields, extrasaction='ignore', delimiter='\t')
            writer.writeheader()
            for trial_info in self.results_summary:
                writer.writerow(trial_info)

    def _draw_component(self, component):

        if component == "touch_and_feel_screen":
            """ ************************************************************ """
            """ Touch and feel screen                                        """
            """ ************************************************************ """
            # Render colors buttons
            top_space = int((self.screen.get_height()/2)-
                         (self.values['margin_y_ui']/2))
            left_space = int((self.screen.get_height()/2)-
                          self.values['color_button_width']-
                          (self.values['margin_x_ui']*1.5))
            count_blue = 0
            count_green = 0
            count_red = 0
            count_yellow = 0
            if self.click_count is not None:
                count_blue = self.click_count[Symbol.BLUE]
                count_green = self.click_count[Symbol.GREEN]
                count_red = self.click_count[Symbol.RED]
                count_yellow = self.click_count[Symbol.YELLOW]
            colors = [
                (self.getColor('color_blue'), Action.VIBRATION_BLUE,
                 count_blue),
                (self.getColor('color_green'), Action.VIBRATION_GREEN,
                 count_green),
                (self.getColor('color_red'), Action.VIBRATION_RED,
                 count_red),
                (self.getColor('color_yellow'), Action.VIBRATION_YELLOW,
                 count_yellow)
                ]
            for i in range(4):
                color_button_rect = Rect(
                    left_space+i*(self.values['color_button_width']+
                                  self.values['margin_x_ui']),
                    top_space,
                    self.values['color_button_width'],
                    self.values['color_button_height']
                    )
                button = pygame.draw.rect(
                    self.screen,
                    colors[i][0],
                    color_button_rect)
                self.active_buttons.append(
                    (colors[i][1], button))
                if colors[i][2] < self.values['minimum_touch_and_feel_clicks']:
                    # Draw border when remaining clicks
                    pygame.draw.rect(
                        self.screen,
                        self.getColor('color_square_highlight_border'),
                        color_button_rect,
                        1)
            # Next button only when minimum clicks reached
            if (count_blue >= self.values['minimum_touch_and_feel_clicks'] and
                count_green >= self.values['minimum_touch_and_feel_clicks'] and
                count_red >= self.values['minimum_touch_and_feel_clicks'] and
                count_yellow >= self.values['minimum_touch_and_feel_clicks']):
                button_rect = self._render_label(
                    self.getString('next_button_label'), # Text
                    self.font_button, # Font
                    self.getColor('color_button_foreground'), # Foreground color
                    self.getColor('color_button_background'), # Background color
                    self.getColor('color_button_decoration'), # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    -1, # Fixed width or -1
                    -1, # Fixed height or -1
                    'left', # 'justified', 'left', 'right' or 'center'
                    Action.NEXT, # Action or None
                    Position.ALIGN_RIGHT, # Relative position x
                    Position.CENTER, # Relative position y
                    self.command_rect # Reference rect
                    )
                # Additional action to clear count
                self.active_buttons.append((Action.CLEAR_CLICK_COUNT,
                                            button_rect))

        elif component == "fixation_cross":
            """ ************************************************************ """
            """ Fixation cross                                               """
            """ ************************************************************ """
            self._draw_text("+", self.font_visual_stimulus,
                            self.getColor('fixation_cross_color'), None)

        elif component == "colored_square_stimulus":
            """ ************************************************************ """
            """ Colored rectangle                                            """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None or
                self.session.active_block.active_trial is None):
                eprint("WARNING: No active trial to draw the component.")
                return
            visual_stimulus_color = (self.session.active_block
                .getActiveTrialValue('visual_stimulus_color'))
            rect_color = None
            if visual_stimulus_color == Symbol.BLUE:
                rect_color = self.getColor('color_blue')
            elif visual_stimulus_color == Symbol.GREEN:
                rect_color = self.getColor('color_green')
            elif visual_stimulus_color == Symbol.RED:
                rect_color = self.getColor('color_red')
            elif visual_stimulus_color == Symbol.YELLOW:
                rect_color = self.getColor('color_yellow')
            else:
                eprint("WARNING: Unknown color symbol.")
                return
            colored_rect = Rect(
                (self.screen.get_width()/2-
                 self.values['rectangle_stimulus_width']/2),
                (self.screen.get_height()/2-
                 self.values['rectangle_stimulus_height']/2),
                self.values['rectangle_stimulus_width'],
                self.values['rectangle_stimulus_height']
                )
            pygame.draw.rect(
                self.screen,
                rect_color,
                colored_rect)

        elif (component == "colored_square_answer_trial_summary"):
            """ ************************************************************ """
            """ Summary with color square for answer                         """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None or
                self.session.active_block.active_trial is None):
                eprint("WARNING: No active trial to draw the component.")
                return
            # Colored square
            vibration_stimulus_color = (self.session.active_block
                .getActiveTrialValue('vibration_stimulus'))
            rect_color = None
            color_text = None
            if vibration_stimulus_color == Symbol.BLUE:
                rect_color = self.getColor('color_blue')
                color_text = self.getString('BLUE')
            elif vibration_stimulus_color == Symbol.GREEN:
                rect_color = self.getColor('color_green')
                color_text = self.getString('GREEN')
            elif vibration_stimulus_color == Symbol.RED:
                rect_color = self.getColor('color_red')
                color_text = self.getString('RED')
            elif vibration_stimulus_color == Symbol.YELLOW:
                rect_color = self.getColor('color_yellow')
                color_text = self.getString('YELLOW')
            else:
                eprint("WARNING: Unknown color symbol.")
                return
            colored_rect = Rect(
                (self.screen.get_width()/2-
                 self.values['rectangle_stimulus_width']/2),
                (self.screen.get_height()/2+
                 self.values['margin_y_ui']),
                self.values['rectangle_stimulus_width'],
                self.values['rectangle_stimulus_height']
                )
            pygame.draw.rect(
                self.screen,
                rect_color,
                colored_rect)
            # Correct answer label
            correct_answer_text = (self.getString('correct_answer_label')+
                                   color_text)
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                correct_answer_text, # Text
                self.font_instruction, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.CENTER, # Relative position x
                Position.TOP, # Relative position y
                colored_rect # Reference rect
                )
            # Reaction time
            """
            if component == "colored_square_answer_rt_trial_summary":
                reaction_time_ms = int((self.session.active_block
                    .getActiveTrialValue('reaction_time')*1000))
                if reaction_time_ms < 0:
                    reaction_time_ms = "-"
                else:
                    reaction_time_ms = str(reaction_time_ms)
                reaction_time_text = (self.getString('reaction_time_ms_label')+
                                       reaction_time_ms)
                reaction_time_surface = self.font_instruction.render(
                    reaction_time_text, True,
                    self.getColor('color_instructions'),
                    self.getColor('color_background'))
                reaction_time_rect = Rect(
                    (self.screen.get_width()/2-
                    reaction_time_surface.get_width()/2),
                    (correct_answer_rect.y-
                     reaction_time_surface.get_height()-
                     self.values['margin_y_ui']),
                    reaction_time_surface.get_width(),
                    reaction_time_surface.get_height()
                    )
                self.screen.blit(reaction_time_surface, reaction_time_rect)
            """

        elif component == "ordered_color_selection_buttons":
            """ ************************************************************ """
            """ Buttons to select the answer                                 """
            """ ************************************************************ """
            # Render colors buttons
            top_space = int((self.screen.get_height()/2)-
                         (self.values['margin_y_ui']/2))
            left_space = int((self.screen.get_height()/2)-
                          self.values['color_button_width']-
                          (self.values['margin_x_ui']*1.5))
            colors = [
                (self.getColor('color_blue'), Action.RESPONSE_BLUE),
                (self.getColor('color_green'), Action.RESPONSE_GREEN),
                (self.getColor('color_red'), Action.RESPONSE_RED),
                (self.getColor('color_yellow'), Action.RESPONSE_YELLOW)
                ]
            for i in range(4):
                color_button_rect = Rect(
                    left_space+i*(self.values['color_button_width']+
                                  self.values['margin_x_ui']),
                    top_space,
                    self.values['color_button_width'],
                    self.values['color_button_height']
                    )
                button = pygame.draw.rect(
                    self.screen,
                    colors[i][0],
                    color_button_rect)
                self.active_buttons.append(
                    (colors[i][1], button))

        elif (component == 'color_selection_trial_summary'):
            """ ************************************************************ """
            """ Is response correct, and correct button       """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None or
                self.session.active_block.active_trial is None):
                eprint("WARNING: No active trial to draw the component.")
                return
            # Trial results
            vibration_stimulus_color = (self.session.active_block
                .getActiveTrialValue('vibration_stimulus'))
            selected_color = (self.session.active_block
                .getActiveTrialValue('response_action'))
            is_correct_response = (selected_color == vibration_stimulus_color)
            reaction_time_ms = int((self.session.active_block
                .getActiveTrialValue('reaction_time')*1000))
            if reaction_time_ms < 0:
                reaction_time_ms = "-"
            else:
                reaction_time_ms = str(reaction_time_ms)
            correct_button_index = None
            correct_button_color = None
            if vibration_stimulus_color == Symbol.BLUE:
                correct_button_index = 0
                correct_button_color = self.getColor('color_blue')
            elif vibration_stimulus_color == Symbol.GREEN:
                correct_button_index = 1
                correct_button_color = self.getColor('color_green')
            elif vibration_stimulus_color == Symbol.RED:
                correct_button_index = 2
                correct_button_color = self.getColor('color_red')
            elif vibration_stimulus_color == Symbol.YELLOW:
                correct_button_index = 3
                correct_button_color = self.getColor('color_yellow')
            # Is response correct label
            is_correct_response_text = None
            if is_correct_response:
                is_correct_response_text = self.getString(
                    'correct_response_label')
            else:
                is_correct_response_text = self.getString(
                    'wrong_response_label')
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                is_correct_response_text, # Text
                self.font_instruction, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.CENTER, # Relative position x
                Position.ALIGN_BOTTOM, # Relative position y
                self.description_top_rect # Reference rect
                )
            # Reaction time label
            """
            if component == 'color_selection_rt_trial_summary':
                reaction_time_text = (self.getString('reaction_time_ms_label')+
                                       reaction_time_ms)
                reaction_time_surface = self.font_instruction.render(
                    reaction_time_text, True,
                    self.getColor('color_instructions'),
                    self.getColor('color_background'))
                reaction_time_rect = Rect(
                    (self.screen.get_width()/2-
                    reaction_time_surface.get_width()/2),
                    (is_correct_response_rect.y-
                     reaction_time_surface.get_height()-
                     self.values['margin_y_ui']),
                    reaction_time_surface.get_width(),
                    reaction_time_surface.get_height()
                    )
                self.screen.blit(reaction_time_surface, reaction_time_rect)
            """
            # Correct button answer
            top_space = int((self.screen.get_height()/2)-
                         (self.values['margin_y_ui']/2))
            left_space = int((self.screen.get_height()/2)-
                          self.values['color_button_width']-
                          (self.values['margin_x_ui']*1.5))
            color_button_rect = Rect(
                left_space+correct_button_index*(
                    self.values['color_button_width']+
                    self.values['margin_x_ui']),
                top_space,
                self.values['color_button_width'],
                self.values['color_button_height']
                )
            button = pygame.draw.rect(
                self.screen,
                correct_button_color,
                color_button_rect)

        elif component == 'intermediate_rt_accuracy_summary':
            """ ************************************************************ """
            """ Intermediate summary with reaction time and accuracy         """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None):
                eprint("WARNING: No active block to draw the component.")
                return
            base_rect = self.description_bottom_rect
            # Reaction time
            global_reaction_time_ms = int(self.session.active_block.
                                getAverageReactionTime()*1000.0)
            partial_reaction_time_ms = int(self.session.active_block.
                                getAverageReactionTime(
                                    'intermediate_rt_accuracy_summary')*1000.0)
            if global_reaction_time_ms >= 0:
                # Display reaction time
                text = (self.getString('reaction_time_ms_label')+
                        str(global_reaction_time_ms)+" ms")
                foreground = self.getColor('color_instructions')
                background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
                decoration = None
                base_rect = self._render_label(
                    text, # Text
                    self.font_instruction_bold, # Font
                    foreground, # Foreground color
                    background, # Background color
                    decoration, # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    -1, # Fixed width or -1
                    -1, # Fixed height or -1
                    'left', # 'justified', 'left', 'right' or 'center'
                    None, # Action or None
                    Position.CENTER, # Relative position x
                    Position.TOP, # Relative position y
                    self.description_bottom_rect # Reference rect
                    )
                # Display icon
                if partial_reaction_time_ms >= 0:
                    diff_reaction_time_ms = (partial_reaction_time_ms-
                                             global_reaction_time_ms)
                    if diff_reaction_time_ms < -50:
                        # Better
                        image = self.getImage('better_icon')
                    else:
                        # Similar
                        image = self.getImage('similar_icon')

                    if image is None:
                        eprint("WARNING: image not found.")
                        return
                    image_rect = Rect(
                        (base_rect.x+base_rect.width+
                         self.values['margin_x_ui']),
                        base_rect.y+base_rect.height/2-image.get_height()/2,
                        image.get_width(),
                        image.get_height()
                        )
                    self.screen.blit(image, image_rect)
            # Accuracy
            global_accuracy = int(self.session.active_block.
                                  getAccuracy()*100.0)
            partial_accuracy = int(self.session.active_block.
                getAccuracy('intermediate_rt_accuracy_summary')*100.0)
            if global_accuracy >= 0:
                # Display accuracy
                text = (self.getString('accuracy_label')+
                        str(global_accuracy)+" %")
                foreground = self.getColor('color_instructions')
                background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
                decoration = None
                base_rect = self._render_label(
                    text, # Text
                    self.font_instruction_bold, # Font
                    foreground, # Foreground color
                    background, # Background color
                    decoration, # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    -1, # Fixed width or -1
                    -1, # Fixed height or -1
                    'left', # 'justified', 'left', 'right' or 'center'
                    None, # Action or None
                    Position.CENTER, # Relative position x
                    Position.TOP, # Relative position y
                    base_rect # Reference rect
                    )
                # Display icon
                if partial_accuracy >= 0:
                    diff_accuracy = (partial_accuracy-global_accuracy)
                    if diff_accuracy > 5 or partial_accuracy == 100:
                        # Better
                        image = self.getImage('better_icon')
                    else:
                        # Similar
                        image = self.getImage('similar_icon')

                    if image is None:
                        eprint("WARNING: image not found.")
                        return
                    image_rect = Rect(
                        (base_rect.x+base_rect.width+
                         self.values['margin_x_ui']),
                        base_rect.y+base_rect.height/2-image.get_height()/2,
                        image.get_width(),
                        image.get_height()
                        )
                    self.screen.blit(image, image_rect)

            # Continue description
            text = self.getString('continue_trial_instructions')
            foreground = self.getColor('color_instructions')
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            decoration = None
            self._render_label(
                text, # Text
                self.font_instruction, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.CENTER, # Relative position x
                Position.ALIGN_TOP, # Relative position y
                self.description_bottom_rect # Reference rect
                )

            # Continue button
            text = self.getString('continue_button_label')
            foreground = self.getColor('color_go_button_foreground')
            background = self.getColor('color_go_button_background')
            decoration = self.getColor('color_go_button_decoration')
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.ALIGN_RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == 'rt_accuracy_summary':
            """ ************************************************************ """
            """ Summary with reaction time and accuracy                      """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None):
                eprint("WARNING: No active block to draw the component.")
                return
            base_rect = self.description_bottom_rect
            # Reaction time
            reaction_time_ms = int(self.session.active_block.
                                getAverageReactionTime()*1000.0)
            if reaction_time_ms >= 0:
                # Display reaction time
                text = (self.getString('reaction_time_ms_label')+
                        str(reaction_time_ms)+" ms")
                foreground = self.getColor('color_instructions')
                background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
                decoration = None
                base_rect = self._render_label(
                    text, # Text
                    self.font_instruction_bold, # Font
                    foreground, # Foreground color
                    background, # Background color
                    decoration, # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    -1, # Fixed width or -1
                    -1, # Fixed height or -1
                    'left', # 'justified', 'left', 'right' or 'center'
                    None, # Action or None
                    Position.CENTER, # Relative position x
                    Position.TOP, # Relative position y
                    self.description_bottom_rect # Reference rect
                    )
            # Accuracy
            accuracy = int(self.session.active_block.
                                getAccuracy()*100.0)
            if accuracy >= 0:
                # Display accuracy
                text = (self.getString('accuracy_label')+
                        str(accuracy)+" %")
                foreground = self.getColor('color_instructions')
                background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
                decoration = None
                self._render_label(
                    text, # Text
                    self.font_instruction_bold, # Font
                    foreground, # Foreground color
                    background, # Background color
                    decoration, # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    -1, # Fixed width or -1
                    -1, # Fixed height or -1
                    'left', # 'justified', 'left', 'right' or 'center'
                    None, # Action or None
                    Position.CENTER, # Relative position x
                    Position.TOP, # Relative position y
                    base_rect # Reference rect
                    )

            # Continue description
            text = self.getString('continue_trial_instructions')
            foreground = self.getColor('color_instructions')
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            decoration = None
            self._render_label(
                text, # Text
                self.font_instruction, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.CENTER, # Relative position x
                Position.ALIGN_TOP, # Relative position y
                self.description_bottom_rect # Reference rect
                )

            # Continue button
            text = self.getString('continue_button_label')
            foreground = self.getColor('color_go_button_foreground')
            background = self.getColor('color_go_button_background')
            decoration = self.getColor('color_go_button_decoration')
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.ALIGN_RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == "fixation_microphone":
            """ ************************************************************ """
            """ Microphone image                                             """
            """ ************************************************************ """
            mic_image = self.getImage('mic')
            if mic_image is None:
                eprint("WARNING: image not found, 'mic'.")
                return
            mic_rect = mic_image.get_rect(center=(
                self.screen.get_width()/2,
                self.screen.get_height()/2))
            self.screen.blit(mic_image, mic_rect)

        elif component == "fixation_button":
            """ ************************************************************ """
            """ Button image                                                 """
            """ ************************************************************ """
            button_image = self.getImage('button')
            if button_image is None:
                eprint("WARNING: image not found, 'button'.")
                return
            button_image_rect = button_image.get_rect(center=(
                self.screen.get_width()/2,
                self.screen.get_height()/2))
            self.screen.blit(button_image, button_image_rect)

        elif component == 'logo':
            """ ************************************************************ """
            """ Logo on top left corner                                      """
            """ ************************************************************ """
            logo_image = self.getImage('logo')
            if logo_image is None:
                eprint("WARNING: image not found, 'logo'.")
                return
            logo_rect = Rect(
                self.title_rect.x,
                (self.title_rect.y+self.title_rect.height/2-
                 logo_image.get_height()/2),
                logo_image.get_width(),
                logo_image.get_height()
                )
            self.screen.blit(logo_image, logo_rect)

        elif component == "colored_color_label":
            """ ************************************************************ """
            """ Standard stroop visual stimulus                              """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None or
                self.session.active_block.active_trial is None):
                eprint("WARNING: No active trial to draw the component.")
                return
            # Colored text
            colored_text = self.session.active_block.getActiveTrialValue('visual_stimulus_text')
            text_color = self.getColor(self.session.active_block
                .getActiveTrialValue('visual_stimulus_color'))
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._draw_text(colored_text, self.font_visual_stimulus,
                            text_color, background)

        elif component == 'start_experiment_title_button':
            """ ************************************************************ """
            """ Start experiment button in title area                        """
            """ ************************************************************ """
            self._render_label(
                self.getString('start_experiment_button_label'), # Text
                self.font_button, # Font
                self.getColor('color_go_button_foreground'), # Foreground color
                self.getColor('color_go_button_background'), # Background color
                self.getColor('color_go_button_decoration'), # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'center', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.CENTER, # Relative position x
                Position.CENTER, # Relative position y
                self.title_rect # Reference rect
                )

        elif component == 'quit_experiment_button':
            """ ************************************************************ """
            """ Quit experiment button in title area                        """
            """ ************************************************************ """
            self._render_label(
                self.getString('quit_experiment_button_label'), # Text
                self.font_button, # Font
                self.getColor('color_button_foreground'), # Foreground color
                self.getColor('color_button_background'), # Background color
                self.getColor('color_button_decoration'), # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'center', # 'justified', 'left', 'right' or 'center'
                Action.QUIT, # Action or None
                Position.ALIGN_LEFT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == 'next_command':
            """ ************************************************************ """
            """ Next button in command area                                  """
            """ ************************************************************ """
            self._render_label(
                self.getString('next_button_label'), # Text
                self.font_button, # Font
                self.getColor('color_button_foreground'), # Foreground color
                self.getColor('color_button_background'), # Background color
                self.getColor('color_button_decoration'), # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.ALIGN_RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == "retry_command":
            """ ************************************************************ """
            """ Retry button in command area                                  """
            """ ************************************************************ """
            self._render_label(
                self.getString('retry_button_label'), # Text
                self.font_button, # Font
                self.getColor('color_button_foreground'), # Foreground color
                self.getColor('color_button_background'), # Background color
                self.getColor('color_button_decoration'), # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.RESTART, # Action or None
                Position.CENTER, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == 'block_list_menu':
            """ ************************************************************ """
            """ Menu with a button for each block                            """
            """ ************************************************************ """

            if self.session is None:
                return
            if self.session.blocks is None or len(self.session.blocks) == 0:
                return
            blocks_titles = []
            blocks_completed = []
            blocks_id = []
            width = 0
            for block in self.session.blocks:
                title = block.config['block_title']
                if self.getString(title):
                    title = self.getString(title)
                blocks_titles.append(title)
                blocks_completed.append(block.state == BlockState.COMPLETED)
                blocks_id.append(block.config['block_id'])
                width = max(width, self._label_rect(
                    title,
                    self.font_button,
                    self.values['padding_x_ui'],
                    self.values['padding_y_ui']).width)
            height = (self._label_rect(blocks_titles[0],
                                      self.font_button,
                                      self.values['padding_x_ui'],
                                      self.values['padding_y_ui']).height +
                      self.values['margin_y_ui'])
            nb_rows = (self.description_rect.height/height)
            nb_columns = (len(self.session.blocks)/nb_rows)+1
            row = 0
            column = 0
            block_idx = 0
            for block in self.session.blocks:
                # Cell rect
                cell_rect = Rect(
                    (self.description_rect.x+
                     (self.description_rect.width/nb_columns)*column),
                    (self.description_rect.y+
                     (self.description_rect.height/nb_rows)*row),
                     self.description_rect.width/nb_columns,
                     self.description_rect.height/nb_rows
                    )
                # Render button
                foreground = (
                    self.getColor('color_button_disabled_foreground') if
                    blocks_completed[block_idx] else
                    self.getColor('color_button_foreground'))
                background = (
                    self.getColor('color_button_disabled_background') if
                    blocks_completed[block_idx] else
                    self.getColor('color_button_background'))
                decoration = (
                    self.getColor('color_button_disabled_decoration') if
                    blocks_completed[block_idx] else
                    self.getColor('color_button_decoration'))
                self._render_label(
                    blocks_titles[block_idx], # Text
                    self.font_button, # Font
                    foreground, # Foreground color
                    background, # Background color
                    decoration, # Decoration color (or None)
                    self.values['padding_x_ui'], # Padding x
                    self.values['padding_y_ui'], # Padding y
                    self.values['margin_x_ui'], # Margin x
                    self.values['margin_y_ui'], # Margin y
                    width, # Fixed width or -1
                    -1, # Fixed height or -1
                    'center', # 'justified', 'left', 'right' or 'center'
                    blocks_id[block_idx], # Action or None
                    Position.CENTER, # Relative position x
                    Position.CENTER, # Relative position y
                    cell_rect # Reference rect
                    )
                # New cell
                block_idx += 1
                row += 1
                if (block_idx == 8 or block_idx == 11):
                    column += 1
                    row = 0

        elif component == 'connect_test_start_command':
            """ ************************************************************ """
            """ Connect, test and start buttons in command area              """
            """ ************************************************************ """
            # Start button
            text = self.getString('start_block_button_label')
            foreground = (
                self.getColor('color_go_button_foreground') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_foreground')
                )
            background = (
                self.getColor('color_go_button_background') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_background')
                )
            decoration = (
                self.getColor('color_go_button_decoration') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_decoration')
                )
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.ALIGN_RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )
            # Test vibration
            text = self.getString('test_belt_button_label')
            foreground = (
                self.getColor('color_button_foreground') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_foreground')
                )
            background = (
                self.getColor('color_button_background') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_background')
                )
            decoration = (
                self.getColor('color_button_decoration') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_decoration')
                )
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.TEST_VIBRATION, # Action or None
                Position.LEFT, # Relative position x
                Position.CENTER, # Relative position y
                button_rect # Reference rect
                )
            # Connect belt
            text = self.getString('connect_button_label')
            foreground = (
                self.getColor('color_button_disabled_foreground') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_foreground')
                )
            background = (
                self.getColor('color_button_disabled_background') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_background')
                )
            decoration = (
                self.getColor('color_button_disabled_decoration') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_decoration')
                )
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.CONNECT_BELT, # Action or None
                Position.LEFT, # Relative position x
                Position.CENTER, # Relative position y
                button_rect # Reference rect
                )

        elif component == 'setting_commands':
            """ ************************************************************ """
            """ Fullscreen, connect and test buttons in command area         """
            """ ************************************************************ """
            # Connect belt
            text = self.getString('connect_button_label')
            foreground = (
                self.getColor('color_button_disabled_foreground') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_foreground')
                )
            background = (
                self.getColor('color_button_disabled_background') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_background')
                )
            decoration = (
                self.getColor('color_button_disabled_decoration') if
                self.isBeltConnected() else
                self.getColor('color_warning_button_decoration')
                )
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.CONNECT_BELT, # Action or None
                Position.CENTER, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )
            # Fullscreen button
            text = self.getString('toggle_fullscreen_button_label')
            foreground = self.getColor('color_button_foreground')
            background = self.getColor('color_button_background')
            decoration = self.getColor('color_button_decoration')
            self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.TOGGLE_FULLSCREEN, # Action or None
                Position.LEFT, # Relative position x
                Position.CENTER, # Relative position y
                button_rect # Reference rect
                )
            # Test vibration
            text = self.getString('test_belt_button_label')
            foreground = (
                self.getColor('color_button_foreground') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_foreground')
                )
            background = (
                self.getColor('color_button_background') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_background')
                )
            decoration = (
                self.getColor('color_button_decoration') if
                self.isBeltConnected() else
                self.getColor('color_button_disabled_decoration')
                )
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'justified', # 'justified', 'left', 'right' or 'center'
                Action.TEST_VIBRATION, # Action or None
                Position.RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                button_rect # Reference rect
                )

        elif component == 'back_to_menu_command':
            """ ************************************************************ """
            """ Back to menu in command area                                 """
            """ ************************************************************ """
            text = self.getString('back_to_menu_button_label')
            foreground = self.getColor('color_button_foreground')
            background = self.getColor('color_button_background')
            decoration = self.getColor('color_button_decoration')
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.CANCEL, # Action or None
                Position.ALIGN_LEFT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == 'block_title':
            """ ************************************************************ """
            """ Block title in title area                                    """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None):
                eprint("WARNING: No active block to draw the component.")
                return
            title = self.session.active_block.config['block_title']
            if self.getString(title):
                title = self.getString(title)
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                title, # Text
                self.font_title, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'center', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.CENTER, # Relative position x
                Position.CENTER, # Relative position y
                self.title_rect # Reference rect
                )

        elif component == 'trials_pause_page':
            """ ************************************************************ """
            """ Pause instructions and continue button                       """
            """ ************************************************************ """
            text = self.getString('pause_instructions')
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                text, # Text
                self.font_instruction, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                0, # Margin x
                0, # Margin y
                self.description_rect.width, # Fixed width or -1
                self.description_rect.height, # Fixed height or -1
                'center', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.ALIGN_LEFT, # Relative position x
                Position.ALIGN_TOP, # Relative position y
                self.description_rect # Reference rect
                )
            text = self.getString('continue_button_label')
            foreground = self.getColor('color_go_button_foreground')
            background = self.getColor('color_go_button_background')
            decoration = self.getColor('color_go_button_decoration')
            button_rect = self._render_label(
                text, # Text
                self.font_button, # Font
                foreground, # Foreground color
                background, # Background color
                decoration, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                Action.NEXT, # Action or None
                Position.ALIGN_RIGHT, # Relative position x
                Position.CENTER, # Relative position y
                self.command_rect # Reference rect
                )

        elif component == 'countdown_fixation_cross':
            """ ************************************************************ """
            """ Countdown with fixation cross in the last second             """
            """ ************************************************************ """
            if (self.session is None or
                self.session.active_block is None or
                self.session.active_block.active_page is None):
                eprint("WARNING: No active page to draw the component.")
                return
            remaining = int(self.session.active_block.active_page
                            .get_remaining_page_time())
            if remaining <= 0:
                # draw fixation cross
                self._draw_text("+", self.font_visual_stimulus,
                            self.getColor('fixation_cross_color'), None)
            else:
                # Draw remaining seconds
                self._draw_text(str(remaining), self.font_visual_stimulus,
                            self.getColor('fixation_cross_color'), None)
            # Continuously redraw
            self.redraw = True

        elif component == 'happy_message':
            """ ************************************************************ """
            """ Encouraging message displayed in the description area        """
            """ ************************************************************ """
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                self.messages[random.randrange(0,3)], # Text
                self.font_title, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                self.values['margin_x_ui'], # Margin x
                self.values['margin_y_ui'], # Margin y
                -1, # Fixed width or -1
                -1, # Fixed height or -1
                'center', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.ALIGN_LEFT, # Relative position x
                Position.CENTER, # Relative position y
                self.title_rect # Reference rect
            )

        elif self.getString(component):
            """ ************************************************************ """
            """ Render text in the description area                          """
            """ ************************************************************ """
            background = (
                    self.getColor('color_background') if
                    self.isBeltConnected() else
                    self.getColor('color_background_warning'))
            self._render_label(
                self.getString(component), # Text
                self.font_instruction, # Font
                self.getColor('color_instructions'), # Foreground color
                background, # Background color
                None, # Decoration color (or None)
                self.values['padding_x_ui'], # Padding x
                self.values['padding_y_ui'], # Padding y
                0, # Margin x
                0, # Margin y
                self.description_rect.width, # Fixed width or -1
                self.description_rect.height, # Fixed height or -1
                'left', # 'justified', 'left', 'right' or 'center'
                None, # Action or None
                Position.ALIGN_LEFT, # Relative position x
                Position.ALIGN_TOP, # Relative position y
                self.description_rect # Reference rect
            )

        else:
            eprint ("WARNING: Unknown component to draw: "+str(component))

    def _draw_text(self, text, font, color, background):
        if not color:
            eprint("WARNING: invalid color")
            return
        text_surface = font.render(text, True, color, background)
        text_rect = text_surface.get_rect(center=(
            self.screen.get_width()/2,
            self.screen.get_height()/2))
        self.screen.blit(text_surface, text_rect)

    def _label_rect(self, text, font,
                    padding_x, padding_y):
        text_rect = font.render(
            text, True, (0, 0, 0)).get_rect()
        text_rect.width += padding_x*2
        text_rect.height += padding_y*2
        return text_rect

    def _render_label(self, text, font,
                      color_foreground, color_background, color_decoration,
                      padding_x, padding_y, margin_x, margin_y,
                      fixed_width, fixed_height, justify,
                      action,
                      rel_position_x, rel_position_y, ref_rect,
                      keep_surface_glyph_id = None):
        # Render text
        text_surface = None
        text_rect = Rect(0, 0,
                         fixed_width-2*padding_x,
                         fixed_height-2*padding_y)
        if text is not None:
            if (keep_surface_glyph_id and
                keep_surface_glyph_id in self.stored_surfaces_glyphs):
                # Retrieve existing surface or glyph
                stored = self.stored_surfaces_glyphs[keep_surface_glyph_id]
                if isinstance(stored, Glyph):
                    text_surface = stored.image
                else:
                    text_surface = stored
                    text_rect = text_surface.get_rect()
            elif (fixed_width is not None and fixed_width > 0 and
                fixed_height is not None and fixed_height > 0):
                # Use Glyph
                text_glyph = Glyph(
                    text_rect,
                    bkg = color_background,
                    color = color_foreground,
                    font = font)
                text_glyph.input(text, justify, True)
                text_surface = text_glyph.image
                if keep_surface_glyph_id:
                    # Store glyph
                    self.stored_surfaces_glyphs[keep_surface_glyph_id] = (
                        text_glyph)
            else:
                # One line text
                text_surface = font.render(
                    text, True, color_foreground,
                    color_background)
                text_rect = text_surface.get_rect()
                if keep_surface_glyph_id:
                    # Store surface
                    self.stored_surfaces_glyphs[keep_surface_glyph_id] = (
                        text_surface)
        # Background rect
        back_rect = ref_rect.copy()

        back_rect.width = text_rect.width+2*padding_x
        if fixed_width is not None:
            back_rect.width = max(back_rect.width, fixed_width+2*padding_x)

        back_rect.height = text_rect.height+2*padding_y
        if fixed_height is not None:
            back_rect.height = max(back_rect.height, fixed_height+2*padding_y)

        if rel_position_x == Position.CENTER:
            # *** CENTER ***
            back_rect.x = ((ref_rect.x+ref_rect.width/2)-
                            back_rect.width/2)

        elif rel_position_x == Position.LEFT:
            # *** LEFT ***
            back_rect.x = (ref_rect.x-margin_x-
                            back_rect.width)

        elif rel_position_x == Position.ALIGN_LEFT:
            # *** ALIGN_LEFT ***
            back_rect.x = ref_rect.x+margin_x

        elif rel_position_x == Position.RIGHT:
            # *** RIGHT ***
            back_rect.x = ref_rect.x+ref_rect.width+margin_x

        elif rel_position_x == Position.ALIGN_RIGHT:
            # *** ALIGN_RIGHT ***
            back_rect.x = ((ref_rect.x+ref_rect.width)-
                            back_rect.width-margin_x)

        if rel_position_y == Position.CENTER:
            # *** CENTER ***
            back_rect.y = ((ref_rect.y+ref_rect.height/2)-
                            back_rect.height/2)

        elif rel_position_y == Position.TOP:
            # *** TOP ***
            back_rect.y = (ref_rect.y-margin_y-
                            back_rect.height)

        elif rel_position_y == Position.ALIGN_TOP:
            # *** ALIGN_TOP ***
            back_rect.y = ref_rect.y+margin_y

        elif rel_position_y == Position.BOTTOM:
            # *** BOTTOM ***
            back_rect.y = ref_rect.y+ref_rect.height+margin_y

        elif rel_position_y == Position.ALIGN_BOTTOM:
            # *** ALIGN_BOTTOM ***
            back_rect.y = ((ref_rect.y+ref_rect.height)-
                            back_rect.height-margin_y)

        # Text position
        text_rect.x = back_rect.x+padding_x
        text_rect.y = back_rect.y+padding_y
        if justify == 'center':
            text_rect.x = (back_rect.x+back_rect.width/2-
                           text_rect.width/2)
        elif justify == 'right':
            text_rect.x = (back_rect.x+back_rect.width-
                           text_rect.width-padding_x)

        # Draw background
        button = pygame.draw.rect(
                self.screen,
                color_background,
                back_rect)
        if action is not None:
            self.active_buttons.append(
                (action, button))
        # Draw text
        self.screen.blit(text_surface, text_rect)
        # Draw decoration for button
        if color_decoration is not None:
            corner_size = self.values['button_corner_size']
            corner_border = self.values['button_corner_border_size']
            pygame.draw.polygon(
                self.screen, color_decoration,
                [(back_rect.x+corner_border, back_rect.y+corner_border),
                 (back_rect.x+corner_border+corner_size,
                  back_rect.y+corner_border),
                 (back_rect.x+corner_border,
                  back_rect.y+corner_border+corner_size),
                 (back_rect.x+corner_border, back_rect.y+corner_border)])
        return back_rect

class Position:
    CENTER = 0
    TOP = 1
    ALIGN_TOP = 2
    BOTTOM = 3
    ALIGN_BOTTOM = 4
    LEFT = 1
    ALIGN_LEFT = 2
    RIGHT = 3
    ALIGN_RIGHT = 4

class Justify:
    LEFT = 'left'
    RIGTH = 'right'
    CENTER = 'center'
    JUSTIFIED = 'justified'
    TOP = 'top'
    BOTTOM = 'bottom'

def main():
    """ experiment. """
    if not len(sys.argv) == 1 and not len(sys.argv) == 3:
        eprint("ERROR: False number of arguments! Either none or "
            "\n   Parameter 1: Session file and \n   Parameter 2: Mapping \nmust be given!")
        return
    try:
        session_file = ""
        mapping_file = ""
        if len(sys.argv) >= 2:
            arg_1 = sys.argv[1]
            arg_2 = sys.argv[2]
            if os.path.isfile(arg_1):
                session_file = ".\\" + arg_1
            else:
                eprint("WARNING: The first argument is not a valid file.")
            if os.path.isfile(arg_2):
                mapping_file = arg_2
            else:
                eprint("WARNING: The second argument is not a valid file.")
        experiment = Experiment(session_file, mapping_file)
        experiment.start()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()
