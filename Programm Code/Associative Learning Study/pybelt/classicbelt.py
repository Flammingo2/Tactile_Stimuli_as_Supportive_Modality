# Communication interface for the feelSpace belt

# Copyright 2017-2019, feelSpace GmbH, <info@feelspace.de>
# All rights reserved. Do not redistribute, sell or publish without the
# prior explicit written consent of the copyright owner.

# Last update: 19.02.2019

#import bluetooth # Bluetooth module from pyBluez
import serial #@UnusedImport # PySerial for USB connection
import serial.tools.list_ports
import threading # For socket listener and event notifier
import time # For timeouts
import math # For fmod on float
import queue
from psychopy import core 
import sys # Only for Python version
from builtins import bytes # For Python 2.7/3 compatibility
import traceback

BELT_UUID = "00001101-0000-1000-8000-00805F9B34FB"
# Belt BT UUID

BELT_BT_COMM_PORT = 1
# Bluetooth communication port

BT_LOOKUP_DURATION = 3
# Bluetooth lookup duration in seconds

VIBROMOTORS_COUNT = 16
# Number of vibromotors on the belt

VIBROMOTORS_ANGLE = 22.5
# Angle between vibromotors

WAIT_ACK_TIMEOUT_SEC = 0.5
# Timeout for waiting ACK

INCOMING_PACKET_TIMEOUT = 0.5
# Timeout to receive a complete packet

HANDSHAKE_TIMEOUT_SEC = 3.0
# Timeout for handshake

THREAD_JOIN_TIMEOUT_SEC = 2.0
# Timeout to wait thread termination

SERIAL_BAUDRATE = 115200
# Baudrate for serial connection

SERIAL_CONNECTION_INIT_WAIT = 5.0
# Waiting time between connection and communication

SERIAL_LOOKUP_WRITE_TIMEOUT = 1.0
# Timeout for write operation when testing ports

SERIAL_READ_TIMEOUT = 1.0
# Timeout to read one byte on serial port

SERIAL_LOOKUP_ACK_TIMEOUT = 2.0
# Timeout to received the ACK during port testing


class BeltController():
    """Class to send commands to the belt via bluetooth.

    Required module
    ---------------
    This module requires PyBluez (https://github.com/karulis/pybluez) and
    PySerial (https://pythonhosted.org/pyserial).

    Bluetooth pairing and passkey
    -----------------------------
    The passkey for the belt is: 0000
    The PyBluez module does not manage passkey so the pairing should be made or
    configured beforehand.
    For instance under Linux the bluetooth-agent can be set before starting
    the connection:
    >>> bluetooth-agent 0000 &
    On Windows, the belt should be paired from the settings panel.

    Serial connection via USB
    -------------------------
    IMPORTANT: If you wear the belt when it is connected via USB, FOR SECURITY
    REASON, you need to ensure that the USB port on which the belt is connected
    is correctly isolated, support data transfer, and provide 5V current up to
    500mA if 6 vibromotors may activated at the same time.
    Please use a USB isolator or check the technical documentation of the USB
    port of your computer to check if the USB port is isolated.

    For a USB connection with the belt, it may be necessary to install a driver.
    First, check that when the belt is connected via USB to your computer a new
    serial port is available. If no serial port appears for the belt, install
    the following VCP driver from Silicon Labs (CP210x USB to UART Bridge
    VCP Drivers):
    https://www.silabs.com/products/development-tools/software/usb-to-uart-bridge-vcp-drivers

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
        :param delegate:
            The delegate that receives belt events.
        """
        # Python version
        self._PY3 = sys.version_info > (3,)
        # Signal orientation parameters
        self._vibromotor_offset = vibromotor_offset;
        self._invert_signal = invert_signal;
        # Delegate
        self._delegate = delegate
        # Variable initialization
        self._belt_connection_state = BeltConnectionState.DISCONNECTED
        self._event_notifier = None
        self._bt_socket = None
        self._serial_port = None
        self._belt_listener = None
        self._belt_mode = BeltMode.UNKNOWN
        self._belt_firm_version = None
        self._default_vibration_intensity = None
        self._belt_heading = None
        self._belt_heading_offset = None
        # Variables for incoming packets
        self._incoming_packet = []
        self._incoming_packet_start_time = time.time();
        # Variables for ACK
        self._wait_ack_id = None
        self._wait_ack_event = threading.Event()
        # Lock for synchronizing output packets (avoid mix of packets)
        self._output_lock = threading.RLock()


    def __del__(self):
        """Disconnect the belt and stop the threads. """
        try:
            self.disconnectBelt()
        except:
            pass



    def connectBeltBT(self, address=None, name=None):
        """Connects a belt via BT.

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
        The function raises an IOError if no bluetooth device can be found.
        A ``BluetoothError`` or ``IOError`` is raised if a problem with
        bluetooth communication occurs.
        """
        self._connect(_BeltConnectionInterface.BT_CLASSIC_INTERFACE,
                      bt_name=name, bt_address=address)


    def connectBeltSerial(self, port=None):
        """Connects a belt via serial port (USB).

        Note that if no port is specified, the lookup procedure may take some
        time (> 5 seconds per tested port).

        Parameters
        ----------
        :param str port:
            The serial port to be used, e.g. 'COM1' on Windows or
            '/dev/ttyUSB0' on Linux.

        Exception
        ---------
        The function raises an IOError if no serial port can be found.
        A ``SerialException`` or ``SerialTimeoutException`` is raised if a
        problem with the serial communication occurs.
        """
        self._connect(_BeltConnectionInterface.USB_INTERFACE,
                      serial_port_name=port)


    def _connect(self, connection_interface, serial_port_name=None,
                 bt_address=None, bt_name=None):
        """Connects to a belt with either USB or BT.

        Parameters
        ----------
        :param int connection_interface:
            The connection interface to be used.
        :param str serial_port_name:
            The serial port name if the connection must be established via USB.
        :param str bt_address:
            The Bluetooth address if the connection must be established via
            Bluetooth.
        :param str bt_name:
            The Bluetooth device name if the connection must be established via
            Bluetooth.
        """
        if connection_interface is None:
            print("BeltController: No connection interface.")
            return
        # Disconnect if necessary
        self.disconnectBelt(True)
        # Start event notifier
        if (self._delegate is not None):
            self._event_notifier = _BeltEventNotifier(self._delegate, self)
            self._event_notifier.start()
        # Connection state
        self._belt_connection_state = BeltConnectionState.CONNECTING
        self._notifyConnectionState()
        # Lookup for device
        if (connection_interface == _BeltConnectionInterface.USB_INTERFACE):
            if serial_port_name is None:
                serial_port_name = findBeltSerialPort()
        elif (connection_interface ==
              _BeltConnectionInterface.BT_CLASSIC_INTERFACE):
            if bt_address is None:
                bt_address = findBeltBTAddress(bt_name)
        else:
            print("BeltController: Unknown connection interface.")
            self.disconnectBelt(True)
            return
        # Connection
        if (connection_interface == _BeltConnectionInterface.USB_INTERFACE):
            if serial_port_name is None:
                print("BeltController: No belt serial port found.")
                self.disconnectBelt(True)
                return
            try:
                # Open port
                self._serial_port = serial.Serial(serial_port_name,
                                                  SERIAL_BAUDRATE,
                                                  timeout=SERIAL_READ_TIMEOUT)
                # Flush input until ready
                time_ready = time.time()+SERIAL_CONNECTION_INIT_WAIT
                while time.time() < time_ready:
                    self._serial_port.read(1)
                # Start listener
                self._belt_listener = _SerialPortListener(self._serial_port,
                                                          self)
                self._belt_listener.start()
            except Exception as e:
                print("BeltController: Serial connection failed.")
                print(str(e))
                self.disconnectBelt(True)
                return
        elif (connection_interface ==
              _BeltConnectionInterface.BT_CLASSIC_INTERFACE):
            if bt_address is None:
                print("BeltController: No Bluetooth device found.")
                self.disconnectBelt(True)
                return
            try:
                self._bt_socket = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
                self._bt_socket.connect((bt_address, BELT_BT_COMM_PORT))
                self._belt_listener = _BTSocketListener(self._bt_socket, self)
                self._belt_listener.start()
            except:
                print("BeltController: Bluetooth connection failed.")
                traceback.print_exc()
                self.disconnectBelt(True)
                return
        # Handshake
        try:
            self._send(b'\x90\x08\xAA\xAA\xAA\x0A', True, 0xD0,
                       HANDSHAKE_TIMEOUT_SEC)
            self._send(b'\x90\x02\xAA\xAA\xAA\x0A', True, 0xD0,
                       HANDSHAKE_TIMEOUT_SEC)
            self._send(b'\x90\x09\xAA\xAA\xAA\x0A', True, 0xD0,
                       HANDSHAKE_TIMEOUT_SEC)
        except Exception as e:
            print("BeltController: Handshake failed.")
            print(str(e))
            self.disconnectBelt(True)
            return
        # Connection state
        self._belt_connection_state = BeltConnectionState.CONNECTED
        self._notifyConnectionState()


    def disconnectBelt(self, join=False):
        """Stops the connection with the belt.

        Parameters
        ----------
        :param bool join:
            'True' to join the socket listener and event notifier threads.
        """
        if (self._belt_connection_state == BeltConnectionState.DISCONNECTING or
            self._belt_connection_state == BeltConnectionState.DISCONNECTED):
            return
        # Set mode and connection state
        self._belt_connection_state = BeltConnectionState.DISCONNECTING
        self._belt_mode = BeltMode.UNKNOWN
        self._notifyConnectionState()
        # Stop listener thread
        if (self._belt_listener is not None):
            self._belt_listener.stop_flag = True
            if join:
                self._belt_listener.join(THREAD_JOIN_TIMEOUT_SEC)
            self._belt_listener = None
        # Close BT socket
        if (self._bt_socket is not None):
            try:
                self._bt_socket.close()
            except:
                print("BeltController: Failed to close BT socket.")
            finally:
                self._bt_socket = None
        # Close serial port
        if (self._serial_port is not None):
            try:
                self._serial_port.close()
            except:
                print("BeltController: Failed to close serial port.")
            finally:
                self._serial_port = None
        # Clear belt values
        self._belt_firm_version = None
        self._default_vibration_intensity = None
        # Set connection state
        self._belt_connection_state = BeltConnectionState.DISCONNECTED
        self._notifyBeltMode()
        self._notifyConnectionState()
        # Stop event notifier
        if (self._event_notifier is not None):
            self._event_notifier.stop_flag = True
            if join:
                self._event_notifier.join(THREAD_JOIN_TIMEOUT_SEC)
            self._event_notifier = None


    def getBeltConnectionState(self):
        """Returns the connection state.
        This method is preferable as reading '_belt_mode' or
        '_belt_connection_state' attributes.

        Return
        ------
        :rtype int
            The belt connection state as enumerated in BeltConnectionState
            class.
        """
        return self._belt_connection_state

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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
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
        if (self._belt_connection_state != BeltConnectionState.CONNECTED or
            self._belt_mode == BeltMode.UNKNOWN):
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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to switch mode. No connection.")
            return
        if (belt_mode is None or belt_mode > 7 or belt_mode < 0):
            print("BeltController: Unable to switch mode. Unknown belt mode.")
            return
        if (belt_mode == self._belt_mode and not force_request):
            return
        # Create packet
        packet = bytes([0x91, 0x08, belt_mode, 0x00, 0xAA, 0x0A])
        # Send packet
        self._send(packet, wait_ack, 0xD1)


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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx<0 or channel_idx>1:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
            if pattern!=0:
                print("BeltController: Unable to send the command. Illegal" +
                      " argument: pattern.")
                return
        else:
            if channel_idx<0 or channel_idx>5:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
            if pattern<0:
                print("BeltController: Unable to send the command. "+
                      "Illegal argument: pattern.")
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
            self._send(packet, wait_ack, ack_id)
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
            self._send(packet, wait_ack, 0xC7)


    def vibrateAtAngle(self, angle, channel_idx=0, intensity=-1, pattern=0,
                       stop_other_channels=False, wait_ack=False):
        """Starts a vibration in a direction relative to the belt.

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


    def vibrateAtPositions(self, indexes, trigger_number, channel_idx=0, intensity=-1,
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
        # Check connection status
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx<0 or channel_idx>1:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
            if pattern!=0:
                print("BeltController: Unable to send the command. "+
                      "Illegal argument: pattern.")
                return
            if len(indexes) < 1:
                print("BeltController: Unable to send the command. "+
                      "Illegal argument: indexes.")
                return
            if len(indexes) > 1 and channel_idx!=0:
                print("BeltController: Unable to send the command. " +
                      "Multiple positions are available only for channel 0.")
                return
        else:
            if channel_idx<0 or channel_idx>5:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
            if pattern<0:
                print("BeltController: Unable to send the command. "+
                      "Illegal argument: pattern.")
                return
            if len(indexes) < 1:
                print("BeltController: Unable to send the command. "+
                      "Illegal argument: indexes.")
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
            self._send(packet, wait_ack, ack_id)
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
            self._send(packet, wait_ack, 0xC7)

    def pulseAtMagneticBearing(self, direction, on_duration_ms, off_duration_ms,
                               iterations=-1, channel_idx=0, intensity=-1,
                               interrupt_current_pulse=False,
                               stop_other_channels=False,
                               wait_ack=False):
        """Starts a regular vibration pulse toward a direction relative to
        magnetic North.

        This command is available only from firmware version 33.

        A 'regular pulse' is a vibration that is active for a duration of
        `on_duration_ms`, and is repeated after a pause of `off_duration_ms`.
        The period of pulses is equal to `on_duration_ms+off_duration_ms`.
        The resolution/precision for `on_duration_ms` and `off_duration_ms` is
        10 milliseconds.
        The direction is expressed in degrees. Value 0 represents the magnetic
        North and positive angles are considered clockwise. E.g. 90 degrees is
        East.
        If the belt is not in APP_MODE, then the mode is changed before sending
        the command.

        Parameters
        ----------
        :param float direction:
            The direction in degrees, in range [0-359].
        :param int on_duration_ms:
            The duration of the pulse vibration in milliseconds.
        :param int off_duration_ms:
            The duration of the pause between pulses.
        :param int iterations:
            The number of time the pulse is repeated, or `-1` to repeat
            indefinitely the pulse. The maximum value is 127.
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are
            available for belt-firmware version 30 and above. Two channels
            (0 and 1) are available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the
            user-defined intensity set on the belt.
        :param bool interrupt_current_pulse:
            If `True` the current pulse on the channel is stopped and the
            vibration of the new pulse is immediately started.
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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<33:
            print("BeltController: The belt firmware version is incompatible "+
                  "for this command. Pulse commands require a minimum "+
                  "firmware version of 33. Actual firmware version is: "+
                  str(self._belt_firm_version))
            return
        if channel_idx<0 or channel_idx>5:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: channel_idx.")
            return
        if on_duration_ms<0:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: on_duration_ms.")
            return
        if off_duration_ms<0:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: off_duration_ms.")
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
        # Adjust iterations
        if iterations > 127:
            iterations = 127
        elif iterations < 0:
            iterations = 0xFF
        # Special cases
        if (iterations == 0 or on_duration_ms == 0):
            if stop_other_channels:
                self.stopVibration(-1, wait_ack)
            else:
                self.stopVibration(channel_idx, wait_ack)
            return
        # Create and send packet
        keep_timer_byte = 1
        if interrupt_current_pulse:
            keep_timer_byte = 0
        sct_byte = 0
        # bit 7 stop other channels
        if stop_other_channels:
            sct_byte += 128
        # bits 4-6 channel index
        sct_byte += channel_idx<<4
        # bits 0-3 direction type
        sct_byte += 3
        packet = bytes([0x8A,
                        sct_byte,
                        (direction_int)&0xFF,
                        (direction_int>>8)&0xFF,
                        intensity,
                        iterations,
                        (on_duration_ms)&0xFF,
                        (on_duration_ms>>8)&0xFF,
                        (on_duration_ms+off_duration_ms)&0xFF,
                        ((on_duration_ms+off_duration_ms)>>8)&0xFF,
                        keep_timer_byte,
                        0x0A])
        # Send packet
        self._send(packet, wait_ack, 0xCA)


    def pulseAtAngle(self, angle, on_duration_ms, off_duration_ms,
                     iterations=-1, channel_idx=0, intensity=-1,
                     interrupt_current_pulse=False,
                     stop_other_channels=False,
                     wait_ack=False):
        """Starts a regular vibration pulse in a direction relative to the belt.

        This command is available only from firmware version 33.

        A 'regular pulse' is a vibration that is active for a duration of
        `on_duration_ms`, and is repeated after a pause of `off_duration_ms`.
        The period of pulses is equal to `on_duration_ms+off_duration_ms`.
        The resolution/precision for `on_duration_ms` and `off_duration_ms` is
        10 milliseconds.
        The angle is expressed in degrees. Value 0 represents the heading of
        the belt and positive angles are considered clockwise. E.g. 90 degrees
        is on the right side.
        If the belt is not in APP_MODE, then the mode is changed before sending
        the command.

        Parameters
        ----------
        :param float angle:
            The angle in degrees, in range [0-359].
        :param int on_duration_ms:
            The duration of the pulse vibration in milliseconds.
        :param int off_duration_ms:
            The duration of the pause between pulses.
        :param int iterations:
            The number of time the pulse is repeated, or `-1` to repeat
            indefinitely the pulse. The maximum value is 127.
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are
            available for belt-firmware version 30 and above. Two channels
            (0 and 1) are available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the
            user-defined intensity set on the belt.
        :param bool interrupt_current_pulse:
            If `True` the current pulse on the channel is stopped and the
            vibration of the new pulse is immediately started.
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
        self.pulseAtPositions(indexes, on_duration_ms, off_duration_ms,
                              iterations, channel_idx, intensity,
                              interrupt_current_pulse, stop_other_channels,
                              wait_ack)


    def pulseAtPositions(self, indexes, on_duration_ms, off_duration_ms,
                         iterations=-1, channel_idx=0, intensity=-1,
                         interrupt_current_pulse=False,
                         stop_other_channels=False,
                         wait_ack=False):
        """Starts a regular vibration pulse at one or multiple positions
        (vibromotor indexes).

        This command is available only from firmware version 33.

        A 'regular pulse' is a vibration that is active for a duration of
        `on_duration_ms`, and is repeated after a pause of `off_duration_ms`.
        The period of pulses is equal to `on_duration_ms+off_duration_ms`.
        The resolution/precision for `on_duration_ms` and `off_duration_ms` is
        10 milliseconds.
        The positions are vibromotors' indexes. Value 0 represents the heading
        vibromotor and indexes are considered clockwise. E.g. index 4 is the
        vibromotor on the right side.
        If the belt is not in APP_MODE, then the mode is changed before sending
        the command.

        Parameters
        ----------
        :param list[int] indexes:
            The indexes of the vibromotors to start, in range [0-15].
        :param int on_duration_ms:
            The duration of the pulse vibration in milliseconds.
        :param int off_duration_ms:
            The duration of the pause between pulses.
        :param int iterations:
            The number of time the pulse is repeated, or `-1` to repeat
            indefinitely the pulse. The maximum value is 127.
        :param int channel_idx:
            The channel to use for the vibration. Six channels (0 to 5) are
            available for belt-firmware version 30 and above. Two channels
            (0 and 1) are available for firmware version below 30.
        :param int intensity:
            The intensity in range [0-100] or a negative value to use the
            user-defined intensity set on the belt.
        :param bool interrupt_current_pulse:
            If `True` the current pulse on the channel is stopped and the
            vibration of the new pulse is immediately started.
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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<33:
            print("BeltController: The belt firmware version is incompatible"+
                  " for this command. Pulse commands require a minimum "+
                  "firmware version of 33. Actual firmware version is: "+
                  str(self._belt_firm_version))
            return
        if len(indexes) < 1:
            print("BeltController: Unable to send the command. "+
                  "Illegal argument: indexes.")
            return
        if channel_idx<0 or channel_idx>5:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: channel_idx.")
            return
        if on_duration_ms<0:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: on_duration_ms.")
            return
        if off_duration_ms<0:
            print("BeltController: Unable to send the command. " +
                  "Illegal argument: off_duration_ms.")
            return
        # Change mode
        if self._belt_mode != BeltMode.APP_MODE:
            self.switchToMode(BeltMode.APP_MODE, False, wait_ack)
        # Adjust indexes
        adjusted_positions = []
        for i in indexes:
            adjusted_positions.append(self._adjustIndex(i))
        # Adjust intensity
        if intensity < 0:
            intensity = 170
        elif intensity > 100:
            intensity = 100
        # Adjust iterations
        if iterations > 127:
            iterations = 127
        elif iterations < 0:
            iterations = 0xFF
        # Special cases
        if (iterations == 0 or on_duration_ms == 0):
            if stop_other_channels:
                self.stopVibration(-1, wait_ack)
            else:
                self.stopVibration(channel_idx, wait_ack)
            return
        # Create and send packet
        keep_timer_byte = 1
        if interrupt_current_pulse:
            keep_timer_byte = 0
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
        packet = bytes([0x8A,
                        sct_byte,
                        (direction_int)&0xFF,
                        (direction_int>>8)&0xFF,
                        intensity,
                        iterations,
                        (on_duration_ms)&0xFF,
                        (on_duration_ms>>8)&0xFF,
                        (on_duration_ms+off_duration_ms)&0xFF,
                        ((on_duration_ms+off_duration_ms)>>8)&0xFF,
                        keep_timer_byte,
                        0x0A])
        # Send packet
        self._send(packet, wait_ack, 0xCA)


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
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        # Check parameters
        if self._belt_firm_version<30:
            if channel_idx>1:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
        else:
            if channel_idx>5:
                print("BeltController: Unable to send the command. " +
                      "Illegal argument: channel_idx.")
                return
        # Send packet
        if self._belt_firm_version<30:
            # Use commands 0x84 and 0x85
            if channel_idx<0 or channel_idx==0:
                self._send(b'\x84\x00\x00\x00\xAA\x0A', wait_ack, 0xC4)
            if channel_idx<0 or channel_idx==1:
                self._send(b'\x85\x00\x00\x00\xAA\x0A', wait_ack, 0xC5)
        else:
            # Use command 0x88
            if channel_idx<0:
                # Stop all channels
                self._send(b'\x88\xFF\xFF\x00\x00\x0A', wait_ack, 0xC8)
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
                self._send(packet, wait_ack, 0xC8)

    def startOrientationNotifications(self, period=0.15, wait_ack=False):
        """Starts the orientation notifications.

        Parameters
        ----------
        :param float period:
            The period of orientation notifications in seconds.
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before
            returning. A timeout is defined, and if reached a
            BeltTimeoutException is raised.
        """
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        if self._belt_firm_version<34:
            print("BeltController: Unable to send the command. " +
                  "Orientation notifications are available only from "+
                  "firmware version 34.")
            return

        packet = bytes([0x92,
                        0x01,
                        (int(period*1000))&0xFF,
                        (int(period*1000)>>8)&0xFF,
                        0x00,
                        0x0A])
        self._send(packet, wait_ack, 0xD2)


    def stopOrientationNotifications(self, wait_ack=False):
        """Stops the orientation notifications.

        Parameters
        ----------
        :param bool wait_ack:
            If 'True' the function waits the command acknowledgment before
            returning. A timeout is defined, and if reached a
            BeltTimeoutException is raised.
        """
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        if self._belt_firm_version<34:
            print("BeltController: Unable to send the command. " +
                  "Orientation notifications are available only from "+
                  "firmware version 34.")
            return
        self._send(b'\x92\x00\x00\x00\x00\x0A', wait_ack, 0xD2)


    def requestOrientation(self):
        """Requests the orientation of the belt.

        This function sends a request to the belt and blocks until the
        orientation of the belt is received.

        Returns
        -------
        :rtype tuple:
            If the orientation request succeed, the returned tuple contains the
            belt heading as first element of the tuple and the heading offset
            in second position.
        """
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            print("BeltController: Unable to send the command. No connection.")
            return
        if self._belt_firm_version<34:
            print("BeltController: Unable to send the command. " +
                  "Orientation notifications are available only from "+
                  "firmware version 34.")
            return
        self._send(b'\x92\x02\x00\x00\x00\x0A', True, 0xD2)
        orientation = (self._belt_heading, self._belt_heading_offset)
        return orientation

    def getOrientation(self):
        """Returns the last known orientation of the belt.

        Returns
        -------
        :rtype tuple:
            Returns a tuple that contains the belt heading as first element of
            the tuple and the heading offset in second position. Returns
            'None' if no orientation notification has been yet received.
        """
        if self._belt_connection_state != BeltConnectionState.CONNECTED:
            return None
        if self._belt_firm_version<34:
            print("BeltController: Unable to know the belt orientation. " +
                  "Orientation notifications are available only from "+
                  "firmware version 34.")
            return
        if self._belt_heading is None or self._belt_heading_offset is None:
            return None
        orientation = (self._belt_heading, self._belt_heading_offset)
        return orientation


    def _adjustAngle(self, angle):
        """Adjusts an angle according to the offset and invert parameters.

        Parameters
        ----------
        :param float angle:
            The angle in degrees.

        Return
        ------
            :rtype int:
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


    def _send(self, packet, wait_ack=False, ack_id=None,
              timeout_sec=WAIT_ACK_TIMEOUT_SEC):
        """Sends a packet and possibly waits for the acknowledgment.

        Parameters
        ----------
        :param bytes packet:
            The packet to send.
        :param bool wait_ack:
            If 'true', waits for the ACK.
        :param int ack_id:
            The acknowledgment ID to wait for, or None to not wait for
            acknowledgment.
        :param float timeout_sec:
            The timeout duration in seconds.

        Exception
        ---------
        Raises a BeltTimeoutException if the timeout is reached when waiting for
        the command acknowledgment.
        """
        if self._belt_connection_state == BeltConnectionState.DISCONNECTED:
            print("BeltCOntroller: Cannot send command without connection.")
            return
        if wait_ack and ack_id is not None:
            # Set ACK flag
            self._wait_ack_id = ack_id
            self._wait_ack_event.clear()
        # Send packet
        with self._output_lock:
            if self._bt_socket is not None:
                # Send via BT
                self._bt_socket.send(packet)
            elif self._serial_port is not None:
                # Send via serial port
                self._serial_port.write(packet)
        # Wait ACK with timeout
        if wait_ack and ack_id is not None:
            if not self._wait_ack_event.is_set():
                # Wait for ACK
                self._wait_ack_event.wait(timeout_sec)
            if not self._wait_ack_event.is_set():
                raise BeltTimeoutException("BeltController: ACK not received '"+
                                           str(ack_id)+"'.")
            # Clear ACK flag
            self._wait_ack_event.clear()
            self._wait_ack_id = None

    def _notifyBeltMode(self, button_id=0, press_type=0):
        """Notifies the belt mode to the delegate.

        Parameters
        ----------
        :param int button_id:
            The button ID if the mode change was caused by a button press.
        :param int press_type:
            The press event if the mode change was caused by a button press.
        """
        if self._event_notifier is not None:
            self._event_notifier.notifyEvent(
                _BeltControllerEvent.BELT_MODE_CHANGED,
                (self._belt_mode,    # New belt mode
                 button_id,                     # Button ID
                 press_type))                    # Press type


    def _notifyConnectionState(self):
        """Notifies the connection state to the delegate.
        """
        self._event_notifier.notifyEvent(
                _BeltControllerEvent.BELT_CONNECTION_STATE_CHANGED,
                (self._belt_connection_state))


    def _handleDataReceived(self, data_received):
        """Handles the data received by either the USB or BT interface.

        Parameters:
        -----------
        :param bytes data_received:
            The data received.
        """
        # Check for packet timeout
        if len(self._incoming_packet) > 0:
            if ((time.time()-self._incoming_packet_start_time) >
                INCOMING_PACKET_TIMEOUT):
                # Timeout, clear previous data
                print("BeltController: Packet timeout.")
                self._incoming_packet = []
        # Check data size
        if data_received is None:
            return
        if len(data_received) < 1:
            return
        # Fill packet
        if len(self._incoming_packet) == 0:
            # Packet start
            self._incoming_packet_start_time = time.time();
        while len(data_received) > 0:
            if len(self._incoming_packet) < 6:
                # Fill packet
                add_bytes = min(6-len(self._incoming_packet),
                                len(data_received))
                self._incoming_packet = (self._incoming_packet +
                                         data_received[:add_bytes])
                data_received = data_received[add_bytes:]
            if len(self._incoming_packet) == 6:
                # Check packet format
                if (self._incoming_packet[5] == 0x0A):
                    # Handle packet
                    self._handlePacketReceived(self._incoming_packet)
                    self._incoming_packet = []
                else:
                    print("BeltController: Malformed packet, no termination "+
                          "byte.")
                    # Clear until '\x0A', to realign
                    try:
                        self._incoming_packet = self._incoming_packet[
                            self._incoming_packet.index(0x0A)+1:]
                    except:
                        self._incoming_packet = []

    def _handlePacketReceived(self, packet_received):
        """Handles a complete packet received by either the USB or BT interface.

        Parameters:
        :param bytes data_received:
            The data received.
        """
        if len(packet_received) != 6:
            print("BeltController: Malformed packet, wrong length.")
            return

        if packet_received[0] == 0x01:
            # Keep-alive notification
            if self._belt_mode != packet_received[2]:
                # Set belt mode
                self._belt_mode = packet_received[2]
                # Notify belt mode
                if self._event_notifier is not None:
                    self._event_notifier.notifyEvent(
                        _BeltControllerEvent.BELT_MODE_CHANGED,
                        (packet_received[2],    # New belt mode
                         0,                     # Button ID
                         0))                    # Press type
            # Keep-alive acknowledgment
            self._send(b'\xF1\xAA\xAA\xAA\xAA\x0A', False)

        elif packet_received[0] == 0x02 or packet_received[0] == 0xC2:
            # Button press notification
            if packet_received[3] <= 7:
                # Set belt mode
                self._belt_mode = packet_received[3]
                # Notify button press
                if self._event_notifier is not None:
                    self._event_notifier.notifyEvent(
                        _BeltControllerEvent.BELT_MODE_CHANGED,
                        (packet_received[3],    # New belt mode
                         packet_received[1],    # Button ID
                         packet_received[2]))   # Press type
            else:
                print("BeltController: Malformed button press notification.")

        elif packet_received[0] == 0xD0 or packet_received[0] == 0xD1:
            # Parameter value
            if packet_received[1] == 0x02:
                # Firmware version
                self._belt_firm_version = packet_received[2]
            elif packet_received[1] == 0x08:
                # Belt mode
                if (packet_received[2] <= 7 and
                    self._belt_mode != packet_received[2]):
                    # Set belt mode
                    self._belt_mode = packet_received[2]
                    # Notify belt mode
                    if self._event_notifier is not None:
                        self._event_notifier.notifyEvent(
                            _BeltControllerEvent.BELT_MODE_CHANGED,
                            (packet_received[2],    # New belt mode
                             0,                     # Button ID
                             0))                    # Press type
            elif packet_received[1] == 0x09:
                # Default vibration intensity
                self._default_vibration_intensity = (
                        packet_received[2])

        elif packet_received[0] == 0x03:
            # Orientation notification
            self._belt_heading = packet_received[1] | (packet_received[2] << 8)
            if self._belt_heading > 32768:
                self._belt_heading -= 65536
            self._belt_heading = self._belt_heading%360
            self._belt_heading_offset = (packet_received[3] |
                                         (packet_received[4] << 8))
            if self._belt_heading_offset > 32768:
                self._belt_heading_offset -= 65536
            self._belt_heading_offset = self._belt_heading_offset%360
            orientation = (self._belt_heading, self._belt_heading_offset)
            self._event_notifier.notifyEvent(
                _BeltControllerEvent.BELT_ORIENTATION_NOTIFIED, orientation)

        # ACK flag
        if self._wait_ack_id is not None:
            if packet_received[0] == self._wait_ack_id:
                self._wait_ack_event.set()


def findBeltBTAddress(name=None):
    """Searches for the Bluetooth address of a belt.

    This function looks at the list of available Bluetooth devices and returns
    the address that corresponds to the given name, or the first with
    ``naviGuertel`` in the name.

    Parameters
    ----------
    :param str name:
        The name of the belt, or a part of the name to look for.

    Exception
    ---------
    A ``BluetoothError`` or ``IOError`` is raised if a problem with
    bluetooth communication occurs.
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

def findBeltSerialPort():
    """Searches for a serial port connected to a belt.

    This function looks at the list of available serial ports and makes a
    request to check if the port is connected to a belt.

    Exception
    ---------
    A ``SerialException`` is raised if a problem with serial communication
    occurs.
    """
    _PY3 = sys.version_info > (3,)
    ports = serial.tools.list_ports.comports()
    for comm_port in ports:
        port_valid = False
        try:
            print("Testing port: "+str(comm_port[0]))
            # Connect to port
            with serial.Serial(comm_port[0],
                           SERIAL_BAUDRATE,
                           timeout=SERIAL_READ_TIMEOUT,
                           write_timeout=SERIAL_LOOKUP_WRITE_TIMEOUT) as conn:
                # Flush input until ready
                time_ready = time.time()+SERIAL_CONNECTION_INIT_WAIT
                while time.time() < time_ready:
                    conn.read(1)
                # Request firmware
                conn.write(b'\x90\x02\xAA\xAA\xAA\x0A')
                # Wait for ACK
                timeout_time = time.time()+SERIAL_LOOKUP_ACK_TIMEOUT
                while ((not port_valid) and (time.time() < timeout_time)):
                    b = conn.read()
                    if not b:
                        # Failed to read a byte within time
                        break
                    if _PY3:
                        if (b[0] == 0xD0):
                            port_valid = True
                    else:
                        if (ord(b) == 0xD0):
                            port_valid = True
        except Exception as e:
            print(e)
            pass
        if port_valid:
            return comm_port[0]
    return None

class BeltConnectionState:
    """Enumeration of connection state."""

    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3

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

class _BeltControllerEvent:
    """Enumeration of belt controller events."""

    BELT_CONNECTION_STATE_CHANGED = 0
    BELT_MODE_CHANGED = 1
    BELT_ORIENTATION_NOTIFIED = 2

class _BeltConnectionInterface:
    """Enumeration of belt connection interfaces."""

    USB_INTERFACE = 0
    BT_CLASSIC_INTERFACE = 1



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
        threading.Thread.__init__(self, name="BTSocketListener")
        self._bt_socket = socket
        self._belt_controller = belt_controller

        # Flag for stopping the thread
        self.stop_flag = False

    def run(self):
        """Starts the thread."""
        self.stop_flag = False
        print("BTSocketListener: Start listening belt.")
        while not self.stop_flag:
            try:
                # Blocking until data are received
                data_str = self._bt_socket.recv(128)
                data = []
                # Convert to list of int
                if data_str is not None and len(data_str) > 0:
                    if self._belt_controller._PY3:
                        for c in data_str:
                            data.append(c)
                    else:
                        for c in data_str:
                            data.append(ord(c))
                    self._belt_controller._handleDataReceived(data)
            except Exception as e:
                if not self.stop_flag:
                    print("BTSocketListener: Error when reading BT input.")
                    print(e)
                self._belt_controller.disconnectBelt()
                break
        print("BTSocketListener: Stop listening belt.")


class _SerialPortListener(threading.Thread):
    """Class for listening serial port."""

    def __init__(self, serial_port, belt_controller):
        """Constructor that configures the port listener.

        Parameters
        ----------
        :param Serial serial_port:
            The port to listen.
        :param BeltController belt_controller:
            The belt controller.
        """
        threading.Thread.__init__(self, name="SerialPortListener")
        self._serial_port = serial_port
        self._belt_controller = belt_controller

        # Flag for stopping the thread
        self.stop_flag = False

    def run(self):
        """Starts the thread."""
        self.stop_flag = False
        print("SerialPortListener: Start listening belt.")
        while not self.stop_flag:
            try:
                # Blocking until data are received
                data_serial = self._serial_port.read()
                data_buffer = []
                # Convert to list of int
                if data_serial is not None and len(data_serial) > 0:
                    if self._belt_controller._PY3:
                        for c in data_serial:
                            data_buffer.append(c)
                    else:
                        for c in data_serial:
                            data_buffer.append(ord(c))
                    self._belt_controller._handleDataReceived(data_buffer)
            except Exception as e:
                if not self.stop_flag:
                    print("SerialPortListener: Error when reading serial "+
                          "input.")
                    print(e)
                self._belt_controller.disconnectBelt()
                break
        print("SerialPortListener: Stop listening belt.")


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
        threading.Thread.__init__(self, name="BeltEventNotifier")
        self._delegate = delegate
        self._belt_controller = belt_controller
        # Notification queue
        self._notification_queue = queue.Queue()
        # Lock for notification queue synchronization
        self._notification_queue_lock = threading.Condition()
        # Flag for stopping the thread
        self.stop_flag = False


    def run(self):
        """Starts the thread."""
        self.stop_flag = False
        print("BeltEventNotifier: Event notifier started.")
        while (not self.stop_flag) or (not self._notification_queue.empty()):
            with self._notification_queue_lock:
                if not self._notification_queue.empty():
                    # Notify next event in queue
                    event = self._notification_queue.get()
                    try:
                        if (event[0] == _BeltControllerEvent.BELT_MODE_CHANGED):
                            self._delegate.onBeltModeChange(event[1])
                        elif (event[0] ==
                              _BeltControllerEvent.BELT_ORIENTATION_NOTIFIED):
                            self._delegate.onBeltOrientationNotified(event[1])
                        elif (event[0] ==
                            _BeltControllerEvent.BELT_CONNECTION_STATE_CHANGED):
                            self._delegate.onBeltConnectionStateChanged(
                                event[1])
                        else:
                            print("BeltEventNotifier: Unknown event ID.")
                    except:
                        pass
                else:
                    # Wait for an item in queue
                    # Note: Lock must has been acquired to wait
                    self._notification_queue_lock.wait(1)
        # Clear reference in controller
        try:
            self._belt_controller._event_notifier = None
        except:
            print("BeltEventNotifier: Unable to clear reference to "
                  "_BeltEventNotifier.")
        print("BeltEventNotifier: Event notifier stopped.")


    def notifyEvent(self, event_id, event_data=None):
        """Notifies asynchronously an event to the delegate.
        """
        if self.is_alive():
            with self._notification_queue_lock:
                self._notification_queue.put((event_id, event_data))
                self._notification_queue_lock.notify_all()
