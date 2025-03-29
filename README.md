# ad-Weather

An AppDaemon weather app that publishes a 'WEATHER_CHANGE' event with valid data upon sensor updates to other AppDaemon apps.

## What Platforms Does It Support?

This app is designed to work with [AppDaemon](https://github.com/AppDaemon/appdaemon) and [Home Assistant](https://www.home-assistant.io/).

- **Home Assistant** is a popular open-source home automation platform offering a wide range of features and integrations with various smart home devices. If you're not already using Home Assistant, I recommend checking it out.

- **AppDaemon** is a loosely coupled, multi-threaded, sandboxed Python execution environment for writing automation apps for various types of home automation software, including Home Assistant and MQTT.

## How Does It Work?

This is a "helper" app to other apps that relies on outside weather data. You can listen to the weather updates with:

```python
        self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE',
            namespace = self.HASS_namespace
        )
```
### Apps configured to use this app:
- [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander)
- [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement)

# Installation and configuration
1. Clone this repository into your [AppDaemon](https://appdaemon.readthedocs.io/en/latest/) `apps` directory.
2. Add configuration to a `.yaml` or `.toml` file to enable the `weather` module.

## Configure weather sensors

The app attempts to find a weather sensor from your HA sensors if you do not provide it with `weather` yourself. It has been tested with [Met.no](https://www.home-assistant.io/integrations/met) integration. This will act as a fallback incase your sensors does not update for 20 minutes. The app is designed to be used witout any other sensors. Most weather forcast integrations does not include rain amount but the app will set amount to 1.0 if state is 'snowy', 'rainy' or 'rainy_snowy'.

Outside temperature is configured with `outside_temperature`. If you configure two, it will check which temperature is lowest of those two if both are updated within the last 20 minutes. The second can be configured with `outside_temperature2`.

You can configure up to two outdoor lux sensors. The second ending with '_2', and the app will keep the highest lux value or retain the last known value if the other is not updated within the last 15 minutes. Both sensors can either be a Home Assistant sensor configured with `OutLux_sensor` or a MQTT sensor `OutLuxMQTT`.

```yaml
weather:
  module: weather
  class: Weather

  weather: weather.forecast_home

  outside_temperature: sensor.outtemp
  outside_temperature2: sensor.outtemp2

  rain_sensor: sensor.rain
  anemometer: sensor.wind

  OutLux_sensor: sensor.lux
  OutLuxMQTT_2: zigbee2mqtt/OutdoorHueLux
```

#### Namespace Configuration
If you have defined a namespace for Home Assistant (HASS), you need to configure the app with `HASS_namespace`. Similarly, if you're using MQTT, define your MQTT namespace with `MQTT_namespace`. Both defaults are set to "default" if not specified.
