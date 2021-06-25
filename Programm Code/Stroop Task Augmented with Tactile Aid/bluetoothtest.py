#!/usr/bin/env python

# Test of the Bluetooth communication interface with a feelSpace belt

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 11.07.2018

import future #@UnusedImport -- For Python 2.7/3 compatibility

from pybelt import bluetoothbelt
import time
import datetime
import tkinter as tk

def main():
    
    """
    This is a minimum example that uses the belt bluetooth connection.
    
    First, a connection is established:
    >>> belt = bluetoothbelt.BeltConnection()
    
    Then, commands are sent to make a rotation around the belt. This first part
    uses the method ``vibrateAtPosition``. For instance, vibration of the third
    vibromotor (index 2) is obtained with:
    >>> belt.vibrateAtPosition(2)
    
    Finally, the belt can be controlled using arrow keys. This second part uses
    an angle for the position of the vibration. For instance, when the right
    arrow key is pressed vibration is oriented at 90 degrees:
    >>> belt.vibrateAtAngle(90)
    
    """
    
    # Connect the belt via bluetooth
    beltAddress = bluetoothbelt.findBeltAddress()
    if beltAddress == None:
        print("No bluetooth device found.")
        return
    belt = bluetoothbelt.BeltController(delegate=Delegate())
    try:
        belt.connectBelt(address=beltAddress)
    except:
        print("Unable to connect to the belt: "+beltAddress)
        raise
    print("Connected to address: "+beltAddress)
    
    # Print firmware version
    firm_version = belt.getFirmwareVersion()
    if (firm_version != None):
        print("Belt firmware version: "+str(firm_version))
    
    # Test vibration (using position)
    print("Start rotation signal.")
    for pos in range(bluetoothbelt.VIBROMOTORS_COUNT):
        belt.vibrateAtPositions([pos])
        time.sleep(0.1)
        
    belt.stopVibration()
    
    # Control with arrow keys (using orientation)
    print("The belt can now be controlled with keys:")
    print("* Arrow keys to vibrate left, right, front or back,")
    print("* 'n' key to vibrate toward North,")
    print("* 'f' for a fade-in fade-out on 4 vibromotors in ~2 second,")
    print("* 'r' for a rotation in ~1.6 second,")
    print("* 'd' for two different intensities (left and right),")
    print("* 'q' to disconnect and stop.")
    print("Focus should must on the Tk window to handle key press.")
    
    def keyPressed(event):
        
        if event.keysym == 'Escape' or event.keysym == 'q':
            # Stop and quit
            belt.stopVibration(wait_ack=True)
            root.destroy()
            
        elif event.keysym == 'n':
            # Vibrate North
            belt.vibrateAtMagneticBearing(0, 0, 50)
            
        if event.keysym == 'Up':
            # Vibrate front
            belt.vibrateAtAngle(0, 0, 50)
            
        elif event.keysym == 'Right':
            # Vibrate right
            belt.vibrateAtAngle(90, 0, 50)
            
        elif event.keysym == 'Down':
            # Vibrate back
            belt.vibrateAtAngle(180, 0, 50)
            
        elif event.keysym == 'Left':
            # Vibrate left
            belt.vibrateAtAngle(270, 0, 50)
            
        elif event.keysym == 'f':
            # Fade-in-out
            for intensity in range(10, 110, 10):
                belt.vibrateAtPositions([0, 4, 8, 12], 0, intensity)
                time.sleep(0.1)
            for intensity in range(100, -10, -10):
                belt.vibrateAtPositions([0, 4, 8, 12], 0, intensity)
                time.sleep(0.1)
            belt.stopVibration(0)
            
        elif event.keysym == 'r':
            # Rotation
            for index in range(0, 16, 1):
                belt.vibrateAtPositions([index], 0, 50)
                time.sleep(0.1)
            belt.stopVibration(0)
            
        elif event.keysym == 'd':
            # Two different intensities (using channel 0 and 1)
            for intensity in range(10, 105, 5):
                # channel 0 for right
                belt.vibrateAtAngle(90, 0, intensity)
                # channel 1 for left
                belt.vibrateAtAngle(270, 1, 100-intensity)
                time.sleep(0.1)
            for intensity in range(100, -5, -5):
                # channel 0 for right
                belt.vibrateAtAngle(90, 0, intensity)
                # channel 1 for left
                belt.vibrateAtAngle(270, 1, 100-intensity)
                time.sleep(0.1)
            belt.stopVibration()
            
        elif event.keysym == 'c':
            # Vibration on 6 channels
            for channel in range(0, 6, 1):
                # Start pattern
                belt.vibrateAtPositions([channel*2], channel, 30, 
                bluetoothbelt.BeltVibrationPattern.CONTINUOUS)
                time.sleep(0.6)
            time.sleep(2)
            for channel in range(0, 6, 1):
                # Start pattern
                belt.vibrateAtPositions([channel*2], channel, 10, 
                bluetoothbelt.BeltVibrationPattern.CONTINUOUS)
                time.sleep(0.6)
            time.sleep(2)
            for channel in range(0, 6, 1):
                # Stop channel
                belt.stopVibration(channel)
                time.sleep(0.6)
            
        elif event.keysym == 'space':
            # Stop vibration
            belt.stopVibration()

        elif event.keysym == '1':
            # Pulse 20-20
            print("Pulse 20-20: 20ms On, 20ms Off, 25 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x14\x00\x28\x00\x01\x0A')

        elif event.keysym == '2':
            # Pulse 30-30
            print("Pulse 30-30: 30ms On, 30ms Off, 16.6 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x1E\x00\x3C\x00\x01\x0A')
            
            
        elif event.keysym == '3':
            # Pulse 40-40
            print("Pulse 40-40: 40ms On, 40ms Off, 12.5 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x28\x00\x50\x00\x01\x0A')
            
        elif event.keysym == '4':
            # Pulse 50-50
            print("Pulse 50-50: 50ms On, 50ms Off, 10 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x32\x00\x64\x00\x01\x0A')

        elif event.keysym == '5':
            # Pulse 60-60
            print("Pulse 60-60: 60ms On, 60ms Off, 8.3 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x3C\x00\x78\x00\x01\x0A')
                
        elif event.keysym == '6':
            # Pulse 60-90
            print("Pulse 60-90: 60ms On, 90ms Off, 6.6 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x3C\x00\x96\x00\x01\x0A')
                
        
        elif event.keysym == '7':
            # Pulse 60-190
            print("Pulse 60-190: 60ms On, 190ms Off, 4 pulses/seconds.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                #                                            v D     v P
                belt._socket.send(b'\x8A\x91\x00\x00\x64\xFF\x3C\x00\xFA\x00\x01\x0A')
                
        elif event.keysym == '8':
            # Single pulse 60
            print("Single pulse 60ms.")
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            with belt._socket_output_lock:
                datePacketSent = datetime.datetime.now()
                try:
                    #                                                v I v D     v P
                    belt._sendAndWait(b'\x8A\x91\x00\x00\x64\x01\x3C\x00\x3C\x00\x00\x0A', 0xCA)
                except Exception as e:
                    print(e)
                dateACKReceived = datetime.datetime.now()
                delayAckMs = (dateACKReceived-datePacketSent).total_seconds()*1000
                print("Delay for ACK: "+str(delayAckMs))
                
        elif event.keysym == 'z':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 0.")
            belt.vibrateAtPositions([0], 0)
        elif event.keysym == 'u':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 1.")
            belt.vibrateAtPositions([1], 0)
        elif event.keysym == 'i':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 2.")
            belt.vibrateAtPositions([2], 0)
        elif event.keysym == 'o':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 3.")
            belt.vibrateAtPositions([3], 0)
        elif event.keysym == 'h':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 4.")
            belt.vibrateAtPositions([4], 0)
        elif event.keysym == 'j':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 5.")
            belt.vibrateAtPositions([5], 0)
        elif event.keysym == 'k':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 6.")
            belt.vibrateAtPositions([6], 0)
        elif event.keysym == 'l':
            if(belt.getBeltMode() != bluetoothbelt.BeltMode.APP_MODE):
                belt.switchToMode(bluetoothbelt.BeltMode.APP_MODE)
            print("Vibrate at position 7.")
            belt.vibrateAtPositions([7], 0)    
            
    root = tk.Tk()
    canvas = tk.Canvas(root)
    text_content=""" The belt can be controlled with keys: \n
* Arrow keys to vibrate left, right, front or back.\n 
* 'n' key to vibrate toward North. \n
* 'f' for a fade-in fade-out on 4 vibromotors in ~2 second.\n 
* 'r' for a rotation in ~1.6 second. \n
* 'd' for two different intensities (left and right).\n 
* 'c' to test the vibration patterns on 6 channels. \n
* 'space' to stop the vibration. \n
* 'q' to disconnect and stop. \n
The focus must be on the Tk window to handle key press."""
    text = canvas.create_text(20, 20, anchor=tk.NW, text=text_content)
    canvas.pack(fill=tk.BOTH, expand=1)
    x1,y1,x2,y2 = canvas.bbox(text)
    canvas.config(width=(x2-x1+40), height=(y2-y1+40))
    root.bind_all('<Key>', keyPressed)
    root.focus_set()
    root.mainloop()
    # Clear BT connection
    belt.stopVibration(wait_ack=True)
    belt.disconnectBelt(True)

class Delegate:
    def onBeltModeChange(self, event):
        """Handler for belt mode change.
        """
        print("*** Belt mode changed ***")
        print("- Mode: "+str(event[0]))
        if (event[1] > 0):
            print("- Changed on button press: "+str(event[1]))

if __name__ == "__main__":
    main()
    
    