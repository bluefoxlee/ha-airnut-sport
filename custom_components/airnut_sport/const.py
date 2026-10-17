"""Constants for the AirNut Sport Bluetooth integration."""

DOMAIN = "airnut_sport"

# The published AirNut Sport implementation uses one custom GATT
# characteristic for both the command write and the notification reply.
CHARACTERISTIC_UUID = "f000c0e1-0451-4000-b000-000000000000"
WRITE_UUID = CHARACTERISTIC_UUID
NOTIFY_UUID = CHARACTERISTIC_UUID

# Read-all command discovered from the vendor app / protocol analysis.
CMD_READ_ALL = bytes((0xAA, 0xAA, 0x6D, 0x55, 0x55))

CONF_MAC = "mac"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_DISCONNECT_DELAY = "disconnect_delay"

DEFAULT_POLLING_INTERVAL = 60
DEFAULT_DISCONNECT_DELAY = 1
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 120
MIN_DISCONNECT_DELAY = 1
