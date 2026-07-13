# QwikSwitch API — Home Assistant integration

[![HACS: Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![GitHub release](https://img.shields.io/github/v/release/rhanekom/hass-qwikswitch-api)](https://github.com/rhanekom/hass-qwikswitch-api/releases)
[![License: MIT](https://img.shields.io/github/license/rhanekom/hass-qwikswitch-api)](LICENSE)

A custom [Home Assistant](https://www.home-assistant.io/) integration that controls QwikSwitch
devices through the cloud [QwikSwitch API](https://qwikswitch.com/doc/), using the
[QwikSwitch Wifi Bridge](https://www.qwikswitch.co.za/products/wifi-bridge).

The [QSUSB integration built into Home Assistant core](https://www.home-assistant.io/integrations/qwikswitch/)
needs a USB modem but controls devices locally. This integration is the alternative for the
Wifi Bridge: the Wifi Bridge offers no local control, so state is polled over the internet
from the QwikSwitch cloud.

## Features

- Exposes QwikSwitch **dimmers as lights** (with brightness) and **relays as switches**.
- **Optimistic updates** — the UI reflects your change immediately, then reconciles with the
  next poll.
- A **priority command queue** that spaces out API calls and debounces duplicates to stay
  within the QwikSwitch rate limit.
- Configurable **poll frequency** and **command delay**, changeable at any time without a
  restart.

## Requirements

- A QwikSwitch [Wifi Bridge](https://www.qwikswitch.co.za/products/wifi-bridge).
- A QwikSwitch account — your registration **email** and your bridge's **master key** (see
  [Configuration](#configuration)).
- Home Assistant **2026.3.0** or newer.

## Installation

### HACS (recommended)

This integration is distributed as a HACS **custom repository**:

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/rhanekom/hass-qwikswitch-api` with category **Integration**.
3. Search for **QwikSwitch API** in HACS, install it, and restart Home Assistant.

### Manual

Copy `custom_components/qwikswitch_api` into your Home Assistant `config/custom_components/`
directory and restart Home Assistant.

## Configuration

Add the integration from **Settings → Devices & services → Add integration → QwikSwitch API**.
You will be asked for two things:

- **Email** — the address you registered on the [QwikSwitch website](https://qwikswitch.com/login/).
- **Master key** — the device id of your Wifi Bridge, registered against that email. This is
  **not** your web-interface password.

### Options

| Option | Default | Minimum | Description |
| ------ | ------- | ------- | ----------- |
| Poll frequency | 5 s | 1 s | How often device state is polled from the API. |
| Command delay | 2 s | 1 s | Minimum spacing between API calls, used to avoid rate limiting. |

You can change these later via the integration's **Configure** button; changes apply
immediately, without a restart.

> [!NOTE]
> The QwikSwitch API is rate limited to roughly **30 requests per minute** — in practice about
> one call every 2 s, rather than a fixed count spread across 60 s. If you see devices going
> unavailable and rate-limit messages in the logs, increase the **command delay**.

On first setup the integration polls the API for all devices. QwikSwitch's API does not return
any friendly names you may have configured, so devices appear under their id (`@...`) — rename
them to something friendlier in Home Assistant.

## Supported devices

| Model | Type in Home Assistant |
| ----- | ---------------------- |
| RELAY QS-D-S5 | Dimmer (light) |
| RELAY QS-R-S5 | Relay (switch) |
| RELAY QS-R-S30 | Relay (switch) |

Using a different device? Open an issue on the
[`qwikswitch-api` library repository](https://github.com/rhanekom/qwikswitch-api) with the
device details.

## Known limitations

1. Because the API is rate limited and this is a polling integration, a light you have just
   switched on may briefly appear to flip back off — the next poll (a few seconds later)
   corrects the state.
2. The API appears to rate limit to about one call every 2 s rather than spreading a call
   count over 60 s. To compensate, the integration queues and spaces out API calls (2 s by
   default).
3. Relays are added as switches. To present one as a light, use Home Assistant's built-in
   **Switch as X** helper to represent the switch as a light.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Released under the [MIT License](LICENSE).
