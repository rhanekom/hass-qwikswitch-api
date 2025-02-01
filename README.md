# QwikSwitch API custom component for Home Assistant

A custom component for Home Assistant that uses the [QwikSwitch API](https://qwikswitch.com/doc/) to discover devices and manage state.

To use this component you will need the [Wifi Bridge](https://www.qwikswitch.co.za/products/wifi-bridge).  This component is an online integration, i.e. polling over the internet).

The [QwikSwitch QSUSB integration included in Home Assistant core](https://www.home-assistant.io/integrations/qwikswitch/) requires a USB modem, but does offer local control. The Wifi Bridge does not offer local integration.


## Installation

Install via HACS.

On setting up the integration you will need two pieces of information:

* The email address you used to register on the [QwikSwitch website](https://qwikswitch.com/login/)
* The "master key", which is the device id of your Wifi Bridge registered against the email address.  This is *not* your password ti the web interface.

The QwikSwitch API has a rate limit of 30 requests per minute.  By default, polling is set at 5s, but can be changed in this configuration.  If you see the devices being disabled for periods, and you being rate limited in the logs, try setting the poll frequency to a higher value.

On setup this integration will call the API to find the status of all devices.  The API does not return any friendly names that you might have set up, so you will need to rename these devices from their id (@....) to more friendly names.

The following devices are currently supported:

* RELAY QS-D-S5 (Dimmer/Light)
* RELAY QS-R-S5 (Relay/Switch)
* RELAY QS-R-S30 (Relay/Switch)

If you have a different device, open up an issue at the [dependent library repo](https://github.com/rhanekom/qwikswitch-api) with details on the device.

## Known issues/limitations

1. With the API being rate-limited and this being a polling integration, you might sometimes see behaviours such as lights toggling back off when you've just switched it on.  A couple of seconds later on the next poll the light state will be corrected.
2. Relays will be added to Home Assistant as switches.  If you want these to be displayed as lights, you change the display type on the entity.

## Contributing

See [Contributing](CONTRIBUTING.md) for details.
