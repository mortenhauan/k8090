# VM8090

A module for interacting with the K8090 and VM8090 relay boards.

## Installation

To install the module, run the following command:

```bash
pip install k8090
```

## Example

```python
from k8090 import relay_card

vmi8090 = relay_card.connect('/dev/tty.usbmodem11301')
vmi8090.factory_reset()

print('Firmware version: ', vmi8090.firmware_version)
print('Jumper status: ', vmi8090.jumper_status)

relay_1 = vmi8090.relays[0]
button_2 = vmi8090.buttons[1]

button_2.mode = 0

relay_1.timer()
```
