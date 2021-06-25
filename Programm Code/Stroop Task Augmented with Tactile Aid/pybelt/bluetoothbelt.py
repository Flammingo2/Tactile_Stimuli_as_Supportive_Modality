# BlueTooth communication interface for the feelSpace belt

# Copyright 2017-2018, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the 
# prior explicit written consent of the copyright owner.

# Last update: 06.04.2018

import bluetooth # Bluetooth module from pyBluez
import threading # For socket listener and event notifier
import time # For timeouts
import math # For fmod on float
import sys # Only for Python version
from builtins import bytes # For Python 2.7/3 compatibility

BELT_UUID = "00001101-0000-1000-8000-00805F9B34FB"
# Belt BT UUID

BELT_BT_COMM_PORT = 1
# Comm port

BT_LOOKUP_DURATION = 3
# BT lookup duration in seconds

VIBROMOTORS_COUNT = 16
# Number of vibromotors on the belt

VIBROMOTORS_ANGLE = 22.5
# Angle between vibromotors

WAIT_ACK_TIMEOUT_SEC = 0.5
# Timeout for waiting ACK

HANDSHAKE_TIMEOUT_SEC = 3.0
# Timeout for handshake


class BeltController():
    """Class to send commands to the belt via bluetooth.
    
    Required module
    ---------------
    This module requires PyBluez (https://github.com/karulis/pybluez).
    
    Bluetooth pairing and passkey
    -----------------------------
    The passkey for the belt is: 0000
    The PyBluez module does not manage passkey so the pairing should be made or 
    configured beforehand.
    For instance under Linux the bluetooth-agent can be set before starting
    the connection:
    >>> bluetooth-agent 0000 &
    On Windows, the belt should be paired from the settings panel.
    
    Orientation of the belt
    -----------------------
    By convention, the vibromotor at the position 0 and an orientation of 0 
    degrees corresponds to the front vibromotor. Indexes and angles increase in 
    the clockwise direction (e.g. the vibromotor index 4, is oriented at 90 
    degrees, on the right).
    If the belt is worn in another position, the ``vibromotor_rotation`` and 
    ``invert_signal`` parameters can be set to adjust the indexes and angles
    of vibration.
    """
    
    def __init__(self, vibromotor_offset=0, invert_signal=False, delegate=None):
        """Constructor that configures the belt controller.
        
        Parameters
        ----------
        :param int vibromotor_offset:
            The offset (number of vibromotors) for adjusting the vibration 
            position. This offset will be added to each position or orientation 
            when methods ``vibrateAt...`` are called. Negative values and values
            greater than the number of vibromotors are accepted.
        :param bool invert_signal:
            If true, all positions or orientation provided for vibration
            commands will be inverted. The inversion is useful when the belt is
            worn in the revert orientation.
        """
        # Python version
        self._PY3 = sys.version_info > (3,)
        # Signal orientation parameters
        self._vibromotor_offset = vibromotor_offset;
        self._invert_signal = invert_signal;
        # Delegate
        self._delegate = delegate
        # Variable initialization
        self._event_notifier = None
        self._socket = None
        self._socket_listener = None
        self._belt_mode = BeltMode.UNKNOWN
        self._belt_firm_version = None
        self._default_vibration_intensity = None
        # Lock for synchronizing output packets (avoid mix of packets)
        self._socket_output_lock = threading.RLock()
        
    
    def __del__(self):
        """Disconnect the belt and stop the threads. """
        try:
            self.disconnectBelt()
        except:
            pass
        
    
    
    def connectBelt(self, address=None, name=None):
        """Opens an RFCOMM socket for sending commands to a belt.
        
        Note that if no address is specified, the lookup procedure may take some 
        time (> 10 seconds).
        
        Parameters
        ----------
        :param str address:
            The Bluetooth address of the belt.
        :param str name:
            The name of the belt, or a part of the name.
        
        Exception
        ---------
        The function raises a IOError if no bluetooth device can be found.
        A ``BluetoothError`` or ``IOError`` is raised if a problem with 
        bluetooth communication occur.
        """
        # Disconnect if necessary
        self.disconnectBelt()
        # Search for the belt address
        if address is None:
            self._belt_address = findBeltAddress(name)
        else:
            self._belt_address = address
        # Open socket
        try:
            self._socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self._socket.connect((self._belt_address, BELT_BT_COMM_PORT))
        except:
            self._socket = None
            raise
        # Start event notifier
        if (self._delegate is not None):
            self._event_notifier = _BeltEventNotifier(self._delegate, self)
            self._event_notifier.start()
        # Start socket listener thread
        self._socket_listener = _BTSocketListener(self._socket, self)
        self._socket_listener.start()
        # Handshake (get belt state, firmware version and default 
        # vibration intensity)
        try:
            self._sendAndWait(b'\x90\x08\xAA\xAA\xAA\x0A', 0xD0, 
                              HANDSHAKE_TIMEOUT_SEC)
            self._sendAndWait(b'\x90\x02\xAA\xAA\xAA\x0A', 0xD0, 
                              HANDSHAKE_TIMEOUT_SEC)
            self._sendAndWait(b'\x90\x09\xAA\xAA\xAA\x0A', 0xD0, 
                              HANDSHAKE_TIMEOUT_SEC)
        except:
            print("Handshake failed.")
        
    
    def disconnectBelt(self, join=False):
        """Stop the bluetooth connection.
        
        Parameters
        ----------
        :param bool join:
            'True' to join the socket listener and event notifier threads.
        """
        # Reset mode
        notify_mode = False
        if self._belt_mode != BeltMode.UNKNOWN:
            self._belt_mode = BeltMode.UNKNOWN
            notify_mode = True
        # Reset firmware version
        self._belt_firm_version = None
        # Stop socket input thread
        if (self._socket_listener is not None):
            self._socket_listener.stop_flag = True
            if join:
                self._socket_listener.join(2)
            self._socket_listener = None
        # Stop event notifier
        if (self._event_notifier is not None):
            self._event_notifier.stop_flag = True
            if join:
                self._event_notifier.join(2)
            self._event_notifier = None
        # Close socket
        if (self._socket is not None):
            try:
                self._socket.close()
            except:
                print("Failed to close BT socket.")
            finally:
                self._socket = None
        # Notify mode
        if notify_mode and self._event_notifier is not None:
            self._event_notifier.notifyBeltModeChange(self._belt_mode)
    
     
    def _setBeltMode(self, belt_mode, button_id=0, press_type=0):
        """Sets the value of the belt mode attribute and notifies it to the 
        delegate.
         
        Note that this method does not change the mode of the belt, for this,
        use the 'switchToMode' method.
         
        Parameters
        ----------
        :param int belt_mode:
            The mode of the belt.
        :param int button_id:
            The button pressed, or 0 if the mode has been changed with no button
            press.
        :param int press_type:
            The type of button press, or 0 if the mode has been changed with no 
            button press.
        """
        if (belt_mode >= -1 and belt_mode <= 7 and 
            belt_mode != self._belt_mode):
            self._belt_mode = belt_mode
            # Notify new mode
            if self._event_notifier is not None:
                self._event_notifier.notifyBeltModeChange(
                    belt_mode, button_id, press_type)
        elif button_id>0 and self._event_notifier is not None:
            # Notify button press
            self._event_notifier.notifyBeltModeChange(
                belt_mode, button_id, press_type)
    
    
    def getBeltMode(self):
        """Returns the mode of the belt.
        This method is preferable as reading the '_belt_mode' attribute because
        the connection state is checked.
        
        Return
        ------
            :rtype int
            The belt mode (including BeltMode.UNKNOWN if the belt is not 
            connected).
        """
        if self._socket is None:
            return BeltMode.UNKNOWN
        else:
            return self._belt_mode 
        
        
    def getFirmwareVersion(self):
        """Returns the firmware version on the belt.
        The firmware version is only available when a belt is connected.
        
        Return
        ------
            :rtype int
            The firmware version, or None if the belt is not connected.
        """
        if self._socket is None or self._belt_mode == BeltMode.UNKNOWN:
            return None
        else:
            return self._belt_firm_version 
        
    
    def switchToMode(self, belt_mode, force_request=False, wait_ack=False):
        """Requests a mode change.
        
        Parameters
        ----------
        :param int belt_mode:
            The requested belt mode. Only mode 1 to 4 should be requested.
        :param bool force_request:
            If 'True' the request is also sent when the local value of the mode
            is equal to the requested mode. 
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before 
            returning. A timeout is defined, and if reached, a 
            BeltTimeoutException is raised.
        
        Exception
        ---------
        The function raises a BeltTimeoutException if the timeout is reached 
        when waiting for the command acknowledgment.
        No exception is raised when parameter values are invalid or the belt is
        not connected.
        """
        # Check state and parameter
        if (self._socket is None):
            print("Unable to switch mode. No connection.")
            return
        if (belt_mode > 7):
            print("Unable to switch mode. Unknown belt mode.")
            return
        if (belt_mode == self._belt_mode and not force_request):
            return
        # Create packet
        packet = bytes([0x91, 0x08, belt_mode, 0x00, 0xAA, 0x0A])
        # Send packet
        if wait_ack:
            self._sendAndWait(packet, 0xD1)
        else:
            with self._socket_output_lock:
                self._socket.send(packet)
        
    
    def vibrateAtMagneticBearing(self, direction, channel_idx=0, intensity=-1,
                                 pattern=0, stop_other_channels=False,
                                 wait_ack=False):
        """Starts a vibration toward a direction relative to magnetic North.
        
        The direction is expressed in degrees. Value 0 represents the magnetic 
        North and positive angles are considered clockwise. E.g. 90 degrees is
        East.
        If the belt is not in APP_MODE, then the mode is changed before sending 
        the command.
        
        Parameters
        ----------
        :param float direction:
            The direction in degrees, in range [0-359].
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are 
            available for belt-firmware version 30 and above. Two channels 
            (0 and 1) are available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the 
            user-defined intensity set on the belt.
        :param int pattern:
            The pattern to use for the vibration, see 
            :class:`BeltVibrationPattern`.
        :param bool stop_other_channels:
            If 'True' the vibrations on other channels are stopped.
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before 
            returning. A timeout is defined, and if reached a 
            BeltTimeoutException is raised.
        
        Exception
        ---------
        The function raises a BeltTimeoutException if the timeout is reached 
        when waiting for the command acknowledgment.
        No exception is raised when parameter values are invalid or the belt is
        not connected.
        """
        # Check connection status
        if self._socket is None:
            print("Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx<0 or channel_idx>1:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
            if pattern!=0:
                print("Unable to send the command. Illegal argument: pattern.")
                return
        else:
            if channel_idx<0 or channel_idx>5:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
            if pattern<0:
                print("Unable to send the command. Illegal argument: pattern.")
                return
        # Change mode
        if self._belt_mode != BeltMode.APP_MODE:
            self.switchToMode(BeltMode.APP_MODE, False, wait_ack)
        # Adjust direction
        direction_int = self._adjustAngle(direction)
        # Adjust intensity
        if intensity < 0:
            intensity = 170
        elif intensity > 100:
            intensity = 100
        # Create and send packet
        if self._belt_firm_version<30:
            # Use commands 0x84 and 0x85
            if channel_idx == 0:
                packet_id = 0x84
                ack_id = 0xC4
                
            else:
                packet_id = 0x85
                ack_id = 0xC5
            # Direction in range [1-360] and not [0-359]
            if direction_int == 0:
                direction_int = 360
            packet = bytes([packet_id,
                            (direction_int << 5)&0xFF,
                            (direction_int >> 3)&0xFF,
                            pattern, 
                            intensity, 
                            0x0A])
            # Send packet
            if wait_ack:
                self._sendAndWait(packet, ack_id)
            else:
                with self._socket_output_lock:
                    self._socket.send(packet)
            # Stop other channels
            if stop_other_channels:
                if channel_idx == 0:
                    self.stopVibration(1, wait_ack)
                else:
                    self.stopVibration(0, wait_ack)
        else:
            # Use command 0x87
            sct_byte = 0
            # bit 7 stop other channels
            if stop_other_channels:
                sct_byte += 128
            # bits 4-6 channel index
            sct_byte += channel_idx<<4
            # bits 0-3 direction type
            sct_byte += 3
            packet = bytes([0x87,
                            sct_byte,
                            (direction_int)&0xFF,
                            (direction_int>>8)&0xFF,
                            intensity, 
                            pattern, 
                            0x0A])
            # Send packet
            if wait_ack:
                self._sendAndWait(packet, 0xC7)
            else:
                with self._socket_output_lock:
                    self._socket.send(packet)
    
    
    def vibrateAtAngle(self, angle, channel_idx=0, intensity=-1, pattern=0, 
                       stop_other_channels=False, wait_ack=False):
        """Starts a vibration in a direction.
        
        The angle is expressed in degrees. Value 0 represents the heading of 
        the belt and positive angles are considered clockwise. E.g. 90 degrees 
        is on the right side.
        If the belt is not in APP_MODE, then the mode is changed before sending 
        the command.
        
        Parameters
        ----------
        :param float angle:
            The angle in degrees, in range [0-359].
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are 
            available for belt-firmware version 30 and above. Two channels 
            (0 and 1) are available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the 
            user-defined intensity set on the belt.
        :param int pattern:
            The pattern to use for the vibration, see 
            :class:`BeltVibrationPattern`.
        :param bool stop_other_channels:
            If 'True' the vibrations on other channels are stopped.
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before 
            returning. A timeout is defined, and if reached a 
            BeltTimeoutException is raised.
        
        Exception
        ---------
        The function raises a BeltTimeoutException if the timeout is reached 
        when waiting for the command acknowledgment.
        No exception is raised when parameter values are invalid or the belt is
        not connected.
        """
        indexes = []
        indexes.append(self._angleToIndex(angle))
        self.vibrateAtPositions(indexes, channel_idx, intensity, pattern, 
                                stop_other_channels, wait_ack)
        
    
    def vibrateAtPositions(self, indexes, channel_idx=0, intensity=-1, 
                          pattern=0, stop_other_channels=False, wait_ack=False):
        """Starts a vibration at one or multiple positions (vibromotor indexes).
        
        The positions are vibromotors' indexes. Value 0 represents the heading  
        vibromotor and indexes are considered clockwise. E.g. index 4 is the 
        vibromotor on the right side.
        
        If the belt is not in APP_MODE, then the mode is changed before sending 
        the command.
        
        Parameters
        ----------
        :param list[int] indexes:
            The indexes of the vibromotors to start, in range [0-15].
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are 
            available for belt-firmware version 30 and above. One channel (0) 
            is available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the 
            user-defined intensity set on the belt.
        :param int pattern:
            The pattern to use for the vibration, see 
            :class:`BeltVibrationPattern`.
        :param bool stop_other_channels:
            If 'True' the vibrations on other channels are stopped.
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before 
            returning. A timeout is defined, and if reached a 
            BeltTimeoutException is raised.
        
        Exception
        ---------
        The function raises a BeltTimeoutException if the timeout is reached 
        when waiting for the command acknowledgment.
        No exception is raised when parameter values are invalid or the belt is
        not connected.
        """

        print(intensity)

        # Check connection status
        if self._socket is None:
            print("Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx<0 or channel_idx>1:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
            if pattern!=0:
                print("Unable to send the command. Illegal argument: pattern.")
                return
            if len(indexes) < 1:
                print("Unable to send the command. Illegal argument: indexes.")
                return
            if len(indexes) > 1 and channel_idx!=0:
                print("Unable to send the command. Multiple positions are " +
                      "available only for channel 0.")
                return
        else:
            if channel_idx<0 or channel_idx>5:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
            if pattern<0:
                print("Unable to send the command. Illegal argument: pattern.")
                return
            if len(indexes) < 1:
                print("Unable to send the command. Illegal argument: indexes.")
                return
        # Change mode
        if self._belt_mode != BeltMode.APP_MODE:
            self.switchToMode(BeltMode.APP_MODE, False, wait_ack)
        # Adjust indexes
        adjusted_positions = []
        if self._belt_firm_version<30:
            for i in indexes:
                adjusted_positions.append(((self._adjustIndex(i)+2)%16)+1)
        else:
            for i in indexes:
                adjusted_positions.append(self._adjustIndex(i))
        # Adjust intensity
        if intensity < 0:
            intensity = 170
        elif intensity > 100:
            intensity = 100
        # Create and send packet
        if self._belt_firm_version<30:
            # Use commands 0x84, 0x85 and 0x86
            if channel_idx == 0 and len(adjusted_positions) == 1:
                packet = bytes([0x84,
                                adjusted_positions[0]&0x1F,
                                0x00,
                                pattern, 
                                intensity,
                                0x0A])
                ack_id = 0xC4
            elif channel_idx == 0:
                mask = 0
                for i in adjusted_positions:
                    mask = mask | (32768 >> (i-1))
                packet = bytes([0x86,
                                (mask>>8)&0xFF,
                                mask&0xFF,
                                0x00, 
                                intensity,
                                0x0A])
                ack_id = 0xC6
            else:
                packet = bytes([0x85,
                                adjusted_positions[0]&0x1F,
                                0x00,
                                pattern, 
                                intensity,
                                0x0A])
                ack_id = 0xC5
            # Send packet
            if wait_ack:
                self._sendAndWait(packet, ack_id)
            else:
                with self._socket_output_lock:
                    self._socket.send(packet)
            # Stop other channels
            if stop_other_channels:
                if channel_idx == 0:
                    self.stopVibration(1, wait_ack)
                else:
                    self.stopVibration(0, wait_ack)
        else:
            # Use command 0x87
            sct_byte = 0
            # bit 7 stop other channels
            if stop_other_channels:
                sct_byte += 128
            # bits 4-6 channel index
            sct_byte += channel_idx<<4
            # bits 0-3 direction type
            if len(adjusted_positions) == 1:
                # Vibromotor index
                sct_byte += 1
                direction_int = adjusted_positions[0]
            else:
                # Binary mask
                sct_byte += 0
                direction_int = 0
                for i in adjusted_positions:
                    direction_int = direction_int | (1<<i)
            packet = bytes([0x87,
                            sct_byte,
                            (direction_int)&0xFF,
                            (direction_int>>8)&0xFF,
                            intensity, 
                            pattern, 
                            0x0A])
            # Send packet
            if wait_ack:
                self._sendAndWait(packet, 0xC7)
            else:
                with self._socket_output_lock:
                    self._socket.send(packet)
            
        
#     def signal(self, signal, direction=0, magneticBearing=False, channel_idx=0, 
#                intensity=-1, stop_other_channels=False, wait_ack=False):
        
        
    def stopVibration(self, channel_idx=-1, wait_ack=False):
        """Stops the vibration.
        This command only stops the vibration in app mode. The wait signal or 
        compass vibration is not impacted by this command.
        
        Parameters
        ----------
        :param int channel_idx:
            The channel to stop, or a negative number to stop all channels.
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before 
            returning. A timeout is defined, and if reached a 
            BeltTimeoutException is raised.
        
        Exception
        ---------
        The function raises a BeltTimeoutException if the timeout is reached 
        when waiting for the command acknowledgment.
        No exception is raised when parameter values are invalid or the belt is
        not connected.
        """
        if self._socket is None:
            print("Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx>1:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
        else:
            if channel_idx>5:
                print("Unable to send the command. Illegal argument: " +
                      "channel_idx.")
                return
        # Send packet
        if self._belt_firm_version<30:
            # Use commands 0x84 and 0x85
            if channel_idx<0 or channel_idx==0:
                if wait_ack:
                    self._sendAndWait(b'\x84\x00\x00\x00\xAA\x0A', 0xC4)
                else:
                    with self._socket_output_lock:
                        self._socket.send(b'\x84\x00\x00\x00\xAA\x0A')
            if channel_idx<0 or channel_idx==1:
                if wait_ack:
                    self._sendAndWait(b'\x85\x00\x00\x00\xAA\x0A', 0xC5)
                else:
                    with self._socket_output_lock:
                        self._socket.send(b'\x85\x00\x00\x00\xAA\x0A')
        else:
            # Use command 0x88
            if channel_idx<0:
                # Stop all channels
                if wait_ack:
                    self._sendAndWait(b'\x88\xFF\xFF\x00\x00\x0A', 0xC8)
                else:
                    with self._socket_output_lock:
                        self._socket.send(b'\x88\xFF\xFF\x00\x00\x0A')
            else:
                # Stop one channel
                mask = 2**channel_idx
                packet = bytes([0x88,
                            mask&0xFF,
                            (mask>>8)&0xFF,
                            0x00, 
                            0x00, 
                            0x0A])
                # Send packet
                if wait_ack:
                    self._sendAndWait(packet, 0xC8)
                else:
                    with self._socket_output_lock:
                        self._socket.send(packet)
            
        
    def _adjustAngle(self, angle):
        """Adjusts an angle according to the offset and invert parameters.
        
        Parameters
        ----------
        :param float angle:
            The angle in degrees.
            
        Return
        ------
            :rtype int
            The adjusted angle in range [0-359].
        """
        angle = (angle+(self._vibromotor_offset*VIBROMOTORS_ANGLE))
        if self._invert_signal:
            angle = angle*-1
        angle_int = int(angle) % 360
        return angle_int
    
    
    def _adjustIndex(self, index):
        """Adjusts an index according to the offset and invert parameters.
        
        Parameters
        ----------
        :param int index:
            The index to adjust.
            
        Return
        ------
            :rtype int
            The adjusted index [0-15].
        """
        index = index+self._vibromotor_offset
        if self._invert_signal:
            index = index*-1
        index = index % VIBROMOTORS_COUNT
        if index < 0:
            index = index+VIBROMOTORS_COUNT
        return index
    
    
    def _angleToIndex(self, angle):
        """Converts an angle to a vibromotor position.
        
        Parameters
        ----------
        :param float angle:
            The angle in degrees.
            
        Return
        ------
            :rtype int
            The index in range [0-15].
        """
        angle = math.fmod(angle, 360.0)
        if (angle < 0):
            angle = angle+360.0
        angle = angle+(VIBROMOTORS_ANGLE/2.0)
        index = int(angle/VIBROMOTORS_ANGLE)
        index = index%VIBROMOTORS_COUNT
        return index
        
    
    def _sendAndWait(self, packet, ack_id, timeout_sec=WAIT_ACK_TIMEOUT_SEC):
        """Sends a packet and waits for the acknowledgment.
        
        Parameters
        ----------
        :param bytes packet:
            The packet to send.
        :param int ack_id:
            The acknowledgment ID to wait for.
        :param float timeout_sec:
            The timeout duration in seconds.
        
        Exception
        ---------
        Raises a BeltTimeoutException if the timeout is reached when waiting for
        the command acknowledgment.
        """
        # ACK flag
        self._socket_listener.wait_ack_id = ack_id
        self._socket_listener.wait_ack_flag = False
        self._socket_listener.wait_ack = True
        # Send packet
        with self._socket_output_lock:
            self._socket.send(packet)
        # Wait ACK with timeout
        timeout_time = time.clock()+timeout_sec
        while (time.clock() < timeout_time and 
               not self._socket_listener.wait_ack_flag):
            time.sleep(.1)
        # Check ACK
        if (not self._socket_listener.wait_ack_flag):
            raise BeltTimeoutException("ACK not received '"+str(ack_id)+"'.")
    
        
def findBeltAddress(name=None):
    """Search for the address of the belt.
    
    This function looks at the list of available addresses and return the one 
    which correspond to the given name, or the first with ``naviGuertel`` in the
    name.
    
    Parameters
    ----------
    :param str name:
        The name of the belt, or a part of the name to look for.

    Exception
    ---------
    A ``BluetoothError`` or ``IOError`` is raised if a problem with 
    bluetooth communication occur.
    """
    # Look at available devices
    available_devices = bluetooth.discover_devices(duration=BT_LOOKUP_DURATION,
                                                   lookup_names=True)
    
    # Check device names
    if (name is None):
        name = 'naviGuertel'
    for device in available_devices:
        device_name = device[1]
        if (device_name.find(name)!=-1):
            return device[0]
    return None
    
    
class BeltMode:
    """Enumeration of the belt modes."""
    
    UNKNOWN = -1
    STANDBY = 0
    WAIT = 1
    COMPASS = 2
    APP_MODE = 3
    PAUSE = 4
    CALIBRATION = 5
    TEMPORARY_COMPASS = 6
    TEMPORARY_LOCATION = 7


class BeltVibrationPattern:
    """Enumeration of vibration pattern types."""
    
    CONTINUOUS = 0
    WAIT_PATTERN = 1
    WAIT_CONNECTED_PATTERN = 2
    SINGLE_SHORT_PULSE_PATTERN = 5
    DOUBLE_SHORT_PULSE_PATTERN = 6
    
    
class BeltTimeoutException(Exception):
    """ Timeout exception that is raised when a command sent to the belt is not
    acknowledge within the timeout period. """
    
    def __init__(self, desc):
        """Constructor of the timeout exception.
        
        Parameters
        ----------
        :param str desc:
            Description of the context of the exception.
        """
        self._desc = desc
        
    def __str__(self):
        return self._desc
    
    
class _BTSocketListener(threading.Thread):
    """Class for listening BT socket."""
    
    
    def __init__(self, socket, belt_controller):
        """Constructor that configures the socket listener.
        
        Parameters
        ----------
        :param BluetoothSocket socket:
            The socket to listen.
        :param BeltController belt_controller:
            The belt controller.
        """
        threading.Thread.__init__(self)
        self._socket = socket
        self._belt_controller = belt_controller
        
        # Flag for stopping the thread
        self.stop_flag = False
        
        # Variables for procedure that waits ACK
        self.wait_ack = False
        self.wait_ack_id = -1
        self.wait_ack_flag = False
        
    def run(self):
        """Starts the thread."""
        self.stop_flag = False
        print("Start listening belt.")
        data = []
        packet = []
        while not self.stop_flag:
            try:
                # Blocking until data are received
                data_str = self._socket.recv(128)
                data = []
                # Convert to list of int
                if self._belt_controller._PY3:
                    for c in data_str:
                        data.append(c) 
                else:
                    for c in data_str:
                        data.append(ord(c))
            except:
                self._belt_controller.disconnectBelt()
                break
            # Handle received data (slice in packets)
            if len(data) > 0:
                while len(data) > 0:
                    if len(packet) < 6:
                        # Fill packet
                        add_bytes = min(6-len(packet), len(data))
                        packet = packet + data[:add_bytes]
                        data = data[add_bytes:]
                    if len(packet) == 6:
                        # Check packet format
                        if (packet[5] == 0x0A):
                            # Handle packet
                            self._handlePacket(packet)
                            packet = []
                        else:
                            # Clear until '\x0A', to realign
                            try:
                                packet = packet[packet.index(0x0A)+1:]
                            except:
                                packet = []
            else:
                break
        print("Stop listening belt.")
    
    
    def _handlePacket(self, packet):
        """Handles received packets.
        
        Parameters
        ----------
        :param list[int] packet:
            The packet to handle.
        """
        # Check packet
        if len(packet) != 6:
            return
        
        # ACK flag
        if self.wait_ack:
            if packet[0] == self.wait_ack_id:
                self.wait_ack_flag = True
                self.wait_ack = False
        
        if packet[0] == 0x01:
            # Keep-alive message
            with self._belt_controller._socket_output_lock:
                self._socket.send(b'\xF1\xAA\xAA\xAA\xAA\x0A')
        
        elif packet[0] == 0x02 or packet[0] == 0xC2:
            # Button press notification
            if packet[3] <= 7:
                self._belt_controller._setBeltMode(packet[3],
                                                   packet[1],
                                                   packet[2])
            
        elif packet[0] == 0xD0 or packet[0] == 0xD1:
            # Parameter value
            if packet[1] == 0x02:
                # Firmware version
                self._belt_controller._belt_firm_version = packet[2]
            elif packet[1] == 0x08:
                # Belt mode
                if (packet[2] <= 7 and 
                    self._belt_controller._belt_mode != packet[2]):
                    self._belt_controller._setBeltMode(packet[2])
            elif packet[1] == 0x09:
                # Default vibration intensity
                self._belt_controller._default_vibration_intensity = packet[2]
    
    
class _BeltEventNotifier(threading.Thread):
    """Class for asynchronous notification of the delegate.
    
    Notifications are made in a separate thread to avoid blocking the listening
    thread when a notification is made. This is especially useful if a vibration
    command is sent in response to a notification. 
    """
    
    
    def __init__(self, delegate, belt_controller):
        """Constructor that configures the belt event notifier.
        
        Parameters
        ----------
        :param object delegate:
            The delegate to inform of events.
        :param BeltController belt_controller:
            The belt controller.
        """
        threading.Thread.__init__(self)
        self._delegate = delegate
        self._belt_controller = belt_controller
        # Notification queue
        self._notification_queue = []
        # Lock for notification queue synchronization
        self._notification_queue_lock = threading.Condition()
        # Flag for stopping the thread
        self.stop_flag = False
        
        
    def run(self):
        """Starts the thread."""
        self.stop_flag = False
        print("Start event notifier.")
        while not self.stop_flag:
            with self._notification_queue_lock:
                if len(self._notification_queue) > 0:
                    # Notify next event in queue
                    event = self._notification_queue[0]
                    del self._notification_queue[0]
                    try:
                        self._delegate.onBeltModeChange(event)
                    except:
                        print("Unable to call 'onBeltModeChange' on delegate.")
                        self.stop_flag = True
                else:
                    # Wait for an item in queue
                    # Note: Lock must has been acquired to wait
                    self._notification_queue_lock.wait(1) 
        # Clear reference in controller
        try:
            self._belt_controller._event_notifier = None
        except:
            print("Unable to clear reference to _BeltEventNotifier.")
        print("Stop event notifier.")
            
    
    def notifyBeltModeChange(self, new_mode, button_id=0, press_type=0):
        """Notifies (asynchronously) of a belt-mode change or button press.
        
        Parameters
        ----------
        :param int new_mode:
            The new belt mode.
        :param int button_id:
            The button pressed, or 0 if the mode has been changed with no button
            press.
        :param int press_type:
            The type of button press, or 0 if the mode has been changed with no 
            button press.
        """
        if self.isAlive():
            with self._notification_queue_lock:
                self._notification_queue.append(
                    (new_mode, button_id, press_type))
                self._notification_queue_lock.notify_all()
            
    
    