# ad-Weather: notes for an AI assistant

Read this with [README.md](README.md). The workflow for finding the user's real entity ids (token, `ha_snapshot.py`, asking when several match) is in the [Pythm_AppdaemonApps LLM guide](https://github.com/Pythm/Pythm_AppdaemonApps/blob/master/LLM_GUIDE.md). Follow its rules: use ids from the index only, ask when several match, one app per `apps.yaml` edit, back up first, no commit or push unasked.

## What the app does

Reads outdoor temperature, lux, rain and wind from HA sensors and/or MQTT topics, falls back to a HA `weather` entity, and fires one `WEATHER_CHANGE` event on the HA namespace. It does not control anything.

## Config (apps.yaml)

```yaml
weather:
  module: weather
  class: Weather
  # everything below is optional
  weather: weather.xxx                # HA weather entity, auto-detected if omitted
  outside_temperature: sensor.xxx     # + outside_temperature_2
  outside_temperature_MQTT: topic     # + outside_temperature_MQTT_2
  OutLux_sensor: sensor.xxx           # + OutLux_sensor_2
  OutLuxMQTT: topic                   # + OutLuxMQTT_2
  rain_sensor: sensor.xxx
  anemometer: sensor.xxx
  estimate_lux: false
  sun_entity: sun.sun
  HASS_namespace: default
  MQTT_namespace: mqtt
```

No key is required. An empty config works if a `weather.*` entity with a temperature exists. Keep the app name `weather`: ClimateCommander looks it up by that name (its `weather_app` arg, default `weather`).

## Which entities fit each key

| Key | Entity or topic | Hints when searching the index |
|---|---|---|
| `weather` | `weather.*` | A forecast integration (Met.no, etc.). Needs a `temperature` attribute. |
| `outside_temperature(_2)` | `sensor.*`, device_class `temperature` | Outdoor only. Never an indoor room sensor. |
| `outside_temperature_MQTT(_2)` | MQTT topic | JSON must contain a `temperature` key, or the payload is a bare number. Zigbee2MQTT topics look like `zigbee2mqtt/<name>`. |
| `OutLux_sensor(_2)` | `sensor.*`, device_class `illuminance` | Outdoor only. |
| `OutLuxMQTT(_2)` | MQTT topic | JSON key `illuminance` (Zigbee) or `value` (Z-Wave), or a bare number. |
| `rain_sensor` | `sensor.*` | State must be a number. A `binary_sensor` (`on`/`off`) does not work. |
| `anemometer` | `sensor.*`, device_class `wind_speed` | Its `unit_of_measurement` decides the unit of the event. |

Several matches: ask the user. Never invent an id or a topic.

Search tips for the index:
- Outdoor devices usually sit in an area such as `Ute`, `Outdoor` or `Garden`. Search by `device_class` and area, not by the word "outside".
- Leave out by default: indoor sensors, window/door sensors, car sensors (`Temperature (outside)` of a vehicle), heat pump outdoor units (`Outside temperature` of a climate integration) and helpers such as `min_max` that combine other sensors. Ask the user if one of them should be used, for example a heat pump as a backup.
- The index has no MQTT topics. Take the topic from the device's friendly name in the MQTT bridge (for Zigbee2MQTT `<base_topic>/<friendly_name>`), say that it is a guess, and ask the user to confirm it. The HA entity of the same device (for example `sensor.<device>_illuminance`) can be used instead if the user prefers it.
- A multi sensor can supply both lux and temperature (for example outdoor Hue motion sensors). Ask whether its temperature should be used: such sensors can read warm in direct sun.

## Two sensors of one kind: ALWAYS ask

Two sensors can mean two different things, and the app cannot tell which. Ask the user for each pair, for example:

> You have two outdoor lux sensors, `<A>` and `<B>`. Is the second one a backup for the first, or does it sit on another side of the house?

- **Backup / redundancy:** configure both here (`OutLux_sensor` + `OutLux_sensor_2`, or the MQTT keys). The app uses the highest fresh lux, or the lowest fresh temperature, and falls back to the other if one goes silent.
- **Another side of the house:** configure only the main sensor here. Put the other sensor in the Lightwand rooms (or ClimateCommander) on that side with `OutLux_sensor` / `OutLuxMQTT`. Those apps use it while it reports and fall back to this app after 20 minutes. Do **not** add it as `_2` here, because then every app gets the combined maximum.
- **Both** (a main pair here for redundancy, plus another side in some rooms): possible, ask which rooms.

Never decide this from the names or areas alone.

## Behaviour to know before editing the config

- Two sensors of one kind: temperature uses the **lowest** fresh value, lux the **highest**. This is by design (shade vs sun), do not "fix" it.
- Fresh means reported within 20 min (temp, rain, wind) or 15 min (lux). When no temp, rain or wind sensor is fresh, the weather entity is used. Lux has no entity fallback.
- `rain` from the weather entity is only `1.0` or `0.0`, from a sensor it is the real amount.
- Values the app has no source for are `None`, not `0`. No event is sent until some value is known.
- MQTT topics only deliver when the device publishes, so they have no value right after a restart.
- `estimate_lux: true` only matters when no lux sensor is configured.
- Wind from the weather entity is converted to the anemometer's unit (km/h if there is none).

## Event for other apps

`WEATHER_CHANGE` on `HASS_namespace` with `temp`, `rain`, `wind`, `wind_unit`, `lux`, `cloud_cover`. Each value except `wind_unit` can be `None`:

```python
self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE', namespace=self.HASS_namespace)

def weather_event(self, event_name, data, **kwargs):
    temp = data.get('temp')
    if temp is None:
        return
```

## Rules for the assistant

- Do not copy the sensors into Lightwand or ClimateCommander. Those apps get weather from this one. Add a lux sensor to a Lightwand room or to ClimateCommander only as an override for another side of the house, and never the same sensor that is already configured here.
- Do not edit `weather.py` to change the min/max rule, the staleness times (`TEMP_STALE_MINUTES`, `LUX_STALE_MINUTES`) or the 3 minute event throttle unless the user asks.
- Check the log after a change: a line `Using weather entity ...` at startup, and no WARNING or ERROR from `weather`.
