"""Constants for the AirNut Sport Bluetooth integration."""

DOMAIN = "airnut_sport"

# The published AirNut Sport implementation uses one custom GATT
# characteristic for both the command write and the notification reply.
CHARACTERISTIC_UUID = "f000c0e1-0451-4000-b000-000000000000"
WRITE_UUID = CHARACTERISTIC_UUID
NOTIFY_UUID = CHARACTERISTIC_UUID

# Standard Bluetooth Device Information Service / Firmware Revision String.
# The device may expose these even though the vendor app does not use them.
DEVICE_INFO_SERVICE_UUID = "0000180a-0000-1000-8000-00805f9b34fb"
FIRMWARE_REVISION_UUID = "00002a26-0000-1000-8000-00805f9b34fb"
HARDWARE_REVISION_UUID = "00002a27-0000-1000-8000-00805f9b34fb"
SOFTWARE_REVISION_UUID = "00002a28-0000-1000-8000-00805f9b34fb"

# Read-all command discovered from the vendor app / protocol analysis.
CMD_READ_ALL = bytes((0xAA, 0xAA, 0x6D, 0x55, 0x55))

CONF_MAC = "mac"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_DISCONNECT_DELAY = "disconnect_delay"
CONF_NIGHT_START_TIME = "night_start_time"
CONF_NIGHT_END_TIME = "night_end_time"
CONF_NIGHT_POLLING_INTERVAL = "night_polling_interval"

DEFAULT_POLLING_INTERVAL = 60
DEFAULT_DISCONNECT_DELAY = 1
DEFAULT_NIGHT_START_TIME = "00:00:00"
DEFAULT_NIGHT_END_TIME = "00:00:00"
DEFAULT_NIGHT_POLLING_INTERVAL = 120
MIN_POLLING_INTERVAL = 10
MAX_POLLING_INTERVAL = 120
MIN_NIGHT_POLLING_INTERVAL = 10
MAX_NIGHT_POLLING_INTERVAL = 120
MIN_DISCONNECT_DELAY = 1
