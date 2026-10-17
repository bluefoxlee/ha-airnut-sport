# AirNut Sport for Home Assistant

Home Assistant custom integration for reading an AirNut Sport device through Bluetooth Low Energy (BLE).

> This project is a preservation and compatibility rewrite. It is not an official AirNut or Moji project.

繁體中文說明：[README_zh-Hant.md](README_zh-Hant.md)

![AirNut Sport icon](custom_components/airnut_sport/brand/icon.png)

## Features

- Temperature
- Humidity
- PM2.5
- Battery level
- Diagnostic BLE revision fields (firmware, hardware, and software revision)
- BLE discovery or manual MAC address configuration
- AirNut-named devices are shown first in the manual Bluetooth device list
- Configurable polling interval and disconnect delay
- Optional night schedule with a slower polling interval

## Installation

Copy `custom_components/airnut_sport` into the `custom_components` directory of Home Assistant, restart Home Assistant, and add **AirNut Sport** from **Settings → Devices & services**.

The device must be awake and advertising during discovery and setup. Home Assistant needs a local Bluetooth adapter or an ESP32 Bluetooth proxy.

Recommended settings based on the original usage notes:

- Polling interval: no more than 130 seconds. This integration limits it to 120 seconds.
- Disconnect delay: at least 1 second.

The options flow also supports a night schedule. During the configured window,
the integration uses the slower night polling interval instead of the normal
one. Set both night times to `00:00` to disable night mode. The window can
cross midnight, for example `22:00` to `07:00`. This changes the BLE polling
frequency; it does not send a display-off command. Keep the night interval at
or below 120 seconds so an unplugged device has a chance to stay awake.

## Source and attribution

The starting point was the `airnut_sport.zip` package supplied by the user. The original package points to the AirNut Sport discussion thread:

- Original discussion: https://bbs.hassbian.com/thread-33040-1-1.html
- Original forum author: [loveyolanda](https://bbs.hassbian.com/home.php?mod=space&uid=28624) (UID: 28624)
- Original source archive: `airnut_sport.zip` supplied by the user
- Brand icon: `1631330723672.jpeg` supplied by the user, converted to PNG for Home Assistant branding

The original archive did not include a license file. Please preserve the original forum attribution and follow the forum author's redistribution terms.
The brand icon is used for product identification only; it does not claim ownership of the Moji/AirNut brand.

## What was rewritten

The following changes were made for the current Home Assistant environment (tested with Home Assistant 2026.10.1):

- Updated the Options Flow to the current Home Assistant API. The old code passed `config_entry` into the Options Flow constructor, which caused the settings dialog to fail with `Invalid handler specified` / HTTP 500.
- Made BLE cleanup synchronous and deterministic: stop notifications, wait for the configured delay, then disconnect.
- Added a per-device update lock so overlapping refreshes do not create competing BLE connections.
- Added response validation and clearer diagnostic logging.
- Probed the standard BLE Device Information Service revision fields in read-only mode. The tested devices returned placeholder labels (`Firmware Revision`, `Hardware Revision`, and `Software Revision`) rather than actual version numbers.
- Restricted device discovery to connectable BLE devices.
- Added safer polling and disconnect-delay validation.
- Kept the first data refresh in the background so an unavailable device does not block entity creation.

The read command and payload layout from the original integration were retained; this repository does not claim to have discovered a new AirNut protocol.

## Protocol notes

The original integration uses:

- Data characteristic: `f000c0e1-0451-4000-b000-000000000000`
- Read command: `AA AA 6D 55 55`
- Response header: `AA AA 6D`

The current integration is read-only. No verified BLE command for remotely turning off the display has been found. When the device is unplugged, stopping polling may allow its normal automatic sleep behavior; the physical rear button may be required to wake it again.

## Safety and limitations

- Do not recharge or reinstall a swollen or damaged lithium battery.
- This is an unofficial integration and is provided without warranty.
- The original source license is currently unknown; no new license is asserted over the original code.

## Credits

- Original AirNut Sport integration: [loveyolanda](https://bbs.hassbian.com/home.php?mod=space&uid=28624), from the forum discussion above.
- Compatibility rewrite and maintenance in this repository: Jerry / Codex, 2026-10-17.
