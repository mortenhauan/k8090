import time
import warnings

import serial


class K8090:

    class Relay:
        """An object representing a relay on the K8090."""
        ON: bool = True
        OFF: bool = False

        def __init__(self, index: int, owner: 'K8090') -> None:
            self._owner = owner
            self._id: int = index
            self._delay: int = 5
            self._timer: bool = False
            self._status: bool = self.OFF
            self._time_remaining: int = 0

        @property
        def id(self) -> int:
            return self._id

        @id.setter
        def id(self, value) -> None:
            if self._id is None:
                return

            self._id = value

        def on(self) -> None:
            self._owner.send_command(0x11, 1 << self.id, 0x00, 0x00)
            self._owner.sync()

        def off(self) -> None:
            self._owner.send_command(0x12, 1 << self.id, 0x00, 0x00)
            self._owner.sync()

        def toggle(self) -> None:
            self._owner.send_command(0x14, 1 << self.id, 0x00, 0x00)
            self._owner.sync()

        def timer(self, seconds: int = None) -> None:
            if seconds is None:
                seconds = 0

            if 0 >= seconds >= 65535:
                raise ValueError('Invalid delay value. Should be int between 0 and 65535.')

            mask = 1 << self.id
            high = (seconds >> 8) & 0xff
            low = (seconds) & 0xff

            self._owner.send_command(0x41, mask, high, low)
            self._owner.sync()

        @property
        def delay(self) -> int:
            return self._delay

        @delay.setter
        def delay(self, seconds: int) -> None:
            if not isinstance(seconds, int):
                raise TypeError('Delay must be an integer')

            if not 0 <= seconds <= 65535:
                raise ValueError('Delay must be between 0 and 65535 seconds')

            self._delay = int(seconds)

            high = (seconds >> 8) & 0xff
            low = (seconds) & 0xff

            self._owner.send_command(0x42, 1 << self.id, high, low)
            self._owner.sync()

        @property
        def timer_is_active(self) -> bool:
            return self._timer

        @timer_is_active.setter
        def timer_is_active(self, value: bool) -> None:
            if not isinstance(value, bool):
                raise TypeError('Timer must be a boolean')

            self._timer = value

        @property
        def status(self) -> bool:
            return self._status

        @status.setter
        def status(self, value) -> None:
            if not isinstance(value, bool):
                raise TypeError('Status must be a boolean')

            self._status = value

    class Button:
        """An object representing a button on the K8090.
        """
        MOMENTARY: int = 0
        TOGGLE: int = 1
        TIMED: int = 2

        INACTIVE: int = 0
        PRESSED: int = 1
        RELEASED: int = 2

        def __init__(self, index, owner: 'K8090') -> None:
            self._owner = owner
            self._id: int = index
            self._mode: int = self.TOGGLE
            self._pressed: bool = False
            self._action: int = self.INACTIVE

        @property
        def id(self) -> int:
            return self._id

        @id.setter
        def id(self, value) -> None:
            if self._id is not None:
                return

            self._id = value

        @property
        def mode(self) -> int:
            return self._mode

        @mode.setter
        def mode(self, mode: int) -> None:
            if mode not in (self.MOMENTARY, self.TOGGLE, self.TIMED):
                raise ValueError(
                    'Invalid button mode. Use one of the Button.MOMENTARY, Button.TOGGLE, Button.TIMED constants.')

            self._mode = mode

            self._owner.sync_button_mode()
            self._owner.sync()

        @property
        def pressed(self) -> bool:
            self._owner.sync()
            return self._pressed

        @pressed.setter
        def pressed(self, value) -> None:
            if not isinstance(value, bool):
                raise TypeError('Pressed value must be a boolean')

            self._pressed = value

        @property
        def action(self) -> int:
            self._owner.sync()
            return self._action

        @action.setter
        def action(self, value: int) -> None:
            if value not in (self.INACTIVE, self.PRESSED, self.RELEASED):
                raise ValueError(
                    'Invalid button action. Use one of the Button.INACTIVE, Button.PRESSED, Button.RELEASED constants.')

            self._action = value

    def __init__(self, port: str):
        """Initiates the K8090 object.

        Args:
            port (str): The serial port to use.
        """
        warnings.warn('VM8090 class is deprecated. Use VM8090.Relay and VM8090.Button classes instead.', DeprecationWarning)
        self.serial = serial.Serial(port, baudrate=19200, timeout=1)
        self.buttons: tuple[K8090.Button, K8090.Button, K8090.Button, K8090.Button, K8090.Button, K8090.Button, K8090.Button,
                            K8090.Button] = (
                                self.Button(0, self),
                                self.Button(1, self),
                                self.Button(2, self),
                                self.Button(3, self),
                                self.Button(4, self),
                                self.Button(5, self),
                                self.Button(6, self),
                                self.Button(7, self),
                            )
        self.relays: tuple[K8090.Relay, K8090.Relay, K8090.Relay, K8090.Relay, K8090.Relay, K8090.Relay, K8090.Relay,
                           K8090.Relay] = (
                               self.Relay(0, self),
                               self.Relay(1, self),
                               self.Relay(2, self),
                               self.Relay(3, self),
                               self.Relay(4, self),
                               self.Relay(5, self),
                               self.Relay(6, self),
                               self.Relay(7, self),
                           )
        self._firmware_version = 'Unknown'

        self._query_relay_status()
        self._query_button_mode()
        self.send_command(0x44, 0xff, 0x00, 0x00)
        self._check_for_response()

    def __del__(self):
        self.serial.close()

    def sync(self) -> None:
        """Syncronize status with the K8090"""
        self._check_for_response()

    @staticmethod
    def _checksum(cmd: int, mask: int, param1: int, param2: int) -> int:
        """The K8090 uses the two's complement for its checksum. This means adding all bytes up to and
        including param2, negating the result and adding 1.

        Args:
            cmd (int): CMD
            mask (int): MASK
            param1 (int): PARAM1
            param2 (int): PARAM2

        Returns:
            int: Returns the checksum
        """
        return ((~(0x04 + cmd + mask + param1 + param2)) + 0x01) & 0xff

    def _check_for_response(self) -> None:
        """Checks the serial port receive buffer for a response from the K8090 and forwards it to _response_handler_
        if it is found.
        """
        time.sleep(0.1)
        while self.serial.in_waiting > 0:

            response = self.serial.read(7)

            try:
                _, cmd, mask, param1, param2, checksum, _ = response

            except ValueError:
                warnings.warn('Invalid response from K8090. Expected 7 bytes, got {}.'.format(len(response)), RuntimeWarning)
                continue

            if checksum != self._checksum(cmd, mask, param1, param2):
                continue

            self._response_handler(cmd, mask, param1, param2)

    def _response_handler(self, cmd: int, mask: int, param1: int, param2: int) -> None:
        """Handles responses from the K8090.

        Args:
            cmd (int): CMD
            mask (int): MASK
            param1 (int): PARAM1
            param2 (int): PARAM2

        Responses:
        `0x22`: Query button mode
        `0x44`: Query timer delay
        `0x50`: Button status
        `0x51`: Relay status
        `0x70`: Jumper status
        `0x71`: Firmware version
        """
        if cmd == 0x22:
            self._query_button_mode_response_handler(mask, param1, param2)

        elif cmd == 0x44:
            self._query_timer_delay_response_handler(mask, param1, param2)

        elif cmd == 0x50:
            self._button_status_response_handler(mask, param1, param2)

        elif cmd == 0x51:
            self._relay_status_response_handler(param1, param2)

        elif cmd == 0x70:
            self._query_jumper_response_handler(param1)

        elif cmd == 0x71:
            self._query_firmware_version_response_handler(param1, param2)

        else:
            warnings.warn('Unknown serial response: {}'.format(cmd), RuntimeWarning)

    def _query_button_mode_response_handler(self, mask: int, param1: int, param2: int) -> None:
        """Query the current mode of each button. Possible modes are momentary, toggle and timed. The mode
        for each button can be set using the 'Set button mode (21h)' command.

        Args:
            mask (int): Button is in momentary mode bit 0-7: Relay 1..8
            param1 (int): Button is in toggle mode bit 0-7: Relay 1..8
            param2 (int): Button is in timed mode bit 0-7: Relay 1..8
        """
        for i in range(8):
            if mask & (1 << i):
                self.buttons[i]._mode = self.Button.MOMENTARY  # pylint: disable=protected-access
            elif param1 & (1 << i):
                self.buttons[i]._mode = self.Button.TOGGLE  # pylint: disable=protected-access
            elif param2 & (1 << i):
                self.buttons[i]._mode = self.Button.TIMED  # pylint: disable=protected-access

    def _query_timer_delay_response_handler(self, mask: int, param1: int, param2: int) -> None:
        """Query the current timer delay for one or more relays. The device will respond with one or more
        packets depending on how many relays have been queried.

        Args:
            mask (int): bit 0-7: Relay 1..8
            param1 (int): High-byte of the timer delay
            param2 (int): Low-byte of the timer delay

        The timer delay field in the response is a 16-bit integer, indicating the requested delay time in
        seconds, for which param1 is the high-byte and param2 is the low-byte value.
        """
        for i in range(8):
            if not mask & (1 << i):
                continue
            self.relays[i]._delay = (param1 << 8) + param2  # pylint: disable=protected-access

    def _button_status_response_handler(self, mask: int, param1: int, param2: int) -> None:
        """This event is sent when a button is pressed or released. Intercept this command to create an eventdriven
        application that monitors the status of the buttons.

        Args:
            mask (int): bit 0-7: State of button 1..8. If the bit is set, the corresponding button is pressed.
            param1 (int): bit 0-7: Button 1..8 has been pressed
            param2 (int): bit 0-7: Button 1..8 has been released
        """
        for i in range(8):
            self.buttons[i].pressed = (mask & (1 << i)) != 0

            if param1 & (1 << i):
                self.buttons[i].action = self.Button.PRESSED
            elif param2 & (1 << i):
                self.buttons[i].action = self.Button.RELEASED

    def _relay_status_response_handler(self, param1: int, param2: int) -> None:
        """This event is sent every time the status of one or more relays changes. Intercept this command to
        create an event-driven application that monitors the status of the relays. The relay status can also be
        queried manually by sending the 'Query relay status (18h)' command; both commands return the
        same response.

        Args:
            param1 (int): bit 0-7: Current state of each relay
            param2 (int): bit 0-7: State of the relay timers (active/inactive)
        """
        for i in range(8):
            self.relays[i].status = (param1 & (1 << i)) != 0
            self.relays[i].timer_is_active = (param2 & (1 << i)) != 0

    def _query_firmware_version_response_handler(self, param1: int, param2: int) -> None:
        """Queries the firmware version of the board. The version number consists of the year and week
        combination of the date the firmware was compiled.

        Args:
            param1 (int): Year (10 = 2010)
            param2 (int): Week (1 = first week of Year)
        """
        year = 2000 + param1
        month = param2
        self._firmware_version = f'{year}.{month}'

    def _query_jumper_response_handler(self, param1: int) -> None:
        """Checks the position of the 'Event' jumper. If the jumper is set, the buttons no longer interact with the
        relays but button events are still sent to the computer.

        Args:
            param1 (int): >= 1: The jumper is set
        """
        self._jumper_status = param1 >= 1

    def send_command(self, cmd: int, mask: int, param1: int, param2: int) -> None:
        """Packets for the K8090 are 7 bytes in size. Each packet is delimited by the `STX (04h)` and `ETX
        (0Fh)` bytes. Validity of the packet can be checked by verifying the checksum byte (`CHK`).

        Packet diagram:
        ```
        | STX (04h) |
        |    CMD    |
        |    MASK   |
        |   PARAM1  |
        |   PARAM2  |
        |    CHK    |
        | ETX (0Fh) |
        ```

        The function of each packet is decided by the command byte (`CMD`), for a list of possible values
        refer to the chapter 'Command List'.

        Each packet has a mask byte (`MASK`), and two parameter bytes (`PARAM1` and `PARAM2`), however
        their meaning differs for each command. The mask byte is usually a bit field indicating which relays
        or buttons should be affected by a command, while the two parameter bytes are simply command
        parameters.
        """
        self.serial.write(bytes([0x04, cmd, mask, param1, param2, self._checksum(cmd, mask, param1, param2), 0x0f]))

    def _query_relay_status(self) -> None:
        """Query the current status of all relays (on/off) and their timers (active/inactive).

        Request parameters:
        ```
        | cmd       | 18h       |
        | mask      | Ignored   |
        | param1    | Ignored   |
        | param2    | Ignored   |
        ```

        The board will respond with a 'Relay status (51h)' packet.
        """
        self.send_command(0x18, 0x00, 0x00, 0x00)
        self._check_for_response()

    def _query_button_mode(self) -> None:
        """Query the current mode of each button. Possible modes are momentary, toggle and timed. The mode
        for each button can be set using the 'Set button mode (21h)' command.

        Request parameters:
        ```
        | cmd       | 22h       |
        | mask      | Ignored   |
        | param1    | Ignored   |
        | param2    | Ignored   |
        ```

        Response parameters:
        ```
        | cmd       | 22h                                               |
        | mask      | Button is in momentary mode bit 0-7: Relay 1..8   |
        | param1    | Button is in toggle mode bit 0-7: Relay 1..8      |
        | param2    | Button is in timed mode bit 0-7: Relay 1..8       |
        ```
        """
        self.send_command(0x22, 0x00, 0x00, 0x00)

    def factory_reset(self) -> None:
        """
        Reset the board to factory defaults

        All buttons are set to `VM8090.Button.TOGGLE` and all timer delays are set to `5 seconds`.
        """
        self.send_command(0x66, 0x00, 0x00, 0x00)
        self._check_for_response()

    def _get_jumper_status(self) -> None:
        """
        Checks the position of the 'Event' jumper. If the jumper is set, the buttons no longer interact with the
        relays but button events are still sent to the computer.

        Request parameters:
        ```
        | cmd       | 70h       |
        | mask      | Ignored   |
        | param1    | Ignored   |
        | param2    | Ignored   |
        ```

        Response parameters:
        ```
        | cmd       | 70h                           |
        | mask      | Reserved                      |
        | param1    | >=1: The jumper is set        |
        | param2    | Reserved                      |
        ```
        """

        self.send_command(0x70, 0x00, 0x00, 0x00)
        self._check_for_response()

    def _get_firmware_version(self) -> None:
        """
        Queries the firmware version of the board. The version number consists of the year and week
        combination of the date the firmware was compiled.

        Request parameters:
        ```
        | cmd       | 71h       |
        | mask      | Ignored   |
        | param1    | Ignored   |
        | param2    | Ignored   |
        ```

        Response parameters:
        ```
        | cmd       | 71h                           |
        | mask      | Reserved                      |
        | param1    | Year (10 = 2010)              |
        | param2    | Week (1 = first week of Year) |
        ```
        """

        self.send_command(0x71, 0x00, 0x00, 0x00)
        self._check_for_response()

    @property
    def firmware_version(self) -> str:
        """Queries the firmware version of the board. The version number consists of the year and week
        combination of the date the firmware was compiled.

        Returns:
            str: String in the format 'YYYY.WW'
        """
        self._get_firmware_version()
        return self._firmware_version

    @property
    def jumper_status(self) -> bool:
        """Checks the position of the 'Event' jumper. If the jumper is set, the buttons no longer interact with the
        relays but button events are still sent to the computer.

        Returns:
            bool: True if the jumper is set
        """
        self._get_jumper_status()
        return self._jumper_status

    def sync_button_mode(self) -> None:
        commands = [0, 0, 0]
        for button in self.buttons:
            commands[button.mode] = commands[button.mode] | (1 << button.id)

        mask, param1, param2 = commands
        self.send_command(0x21, mask, param1, param2)
        self.sync()


def connect(serial_port: str) -> K8090:
    """Connect to a VM8090 board.

    Args:
        serial_port (str): The serial port that the VM8090 is connected to.

    Returns:
        VM8090: A VM8090 object
    """
    return K8090(serial_port)
