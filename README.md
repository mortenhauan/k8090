# K8090

A module for interacting with the K8090 and VM8090 relay boards.

## Installation

To install the module, run the following command:

```bash
pip install k8090
```

## Example

```python
# Import relay_card from k8090
import time
from k8090 import relay_card

# Connecting to card
card = relay_card.connect('/dev/tty.usbmodem11301')

# Doing factory reset
card.factory_reset()

# Reading information about card
print(f'Firmware version: {card.firmware_version}')
print(f'Jumper status: {card.jumper_status}\n')

# Copying relay 4 into a variable
relay_4 = card.relays[3]

# Toggle relay 4
relay_4.on()
card.relays[3].off()
relay_4.toggle()
card.relays[3].toggle()

# Turn on relay 4 and then turn off after 10 seconds
relay_4.delay = 10
relay_4.timer()

# Getting status of all relays
for relay in card.relays:
    print(f'Relay number: {relay.id+1}')
    print(f'Relay status: {relay.status}')
    print(f'Relay delay: {relay.delay}')
    print(f'Timer is active: {relay.timer_is_active}\n')

print(f'Relay 4 delay: {relay_4.delay}')

# Copying button 4 into a variable
button_4 = card.buttons[3]

# Changing mode of button 4 to momentary
button_4.mode = card.Button.MOMENTARY

# Getting status of button 1 every second for 10 seconds
button_1 = card.buttons[0]
for _ in range(10):
    print(f'Button 1 pressed: {button_1.pressed}')
    print(f'Button 1 mode: {button_1.mode}')
    print(f'Button 1 last action: {button_1.action}\n')
    time.sleep(1)

# Getting status of all buttons
for button in card.buttons:
    print(f'Button number: {button.id+1}')
    print(f'Button 1 pressed: {button.pressed}')
    print(f'Button 1 mode: {button.mode}')
    print(f'Button 1 last action: {button.action}\n')

```
