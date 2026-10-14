
# ad-Weather  
**An AppDaemon app that centralises all outdoor weather data and publishes a single `WEATHER_CHANGE` event that can be consumed by any other AppDaemon apps.**  
---

## 🌍 Features  
- **Publishes `WEATHER_CHANGE` event**: Updates other AppDaemon apps with weather data (e.g., temperature, rain, wind, lux) when sensors change.  
- **Multi‑sensor support**: Up to two temperature and lux sensors for accurate outdoor temperature and lux tracking.
- **Home Assistant or MQTT sensors**: For lux and temperature you can use a combination of HA and MQTT sensors.
- **Fallback to a weather entity**: Automatically detects a `weather` entity from Home Assistant (for example Met.no) if no explicit `weather` is provided.
- **Stale‑sensor handling** Uses a configurable timeout (20 min for temp/rain/wind, 15 min for lux).
- **Namespace flexibility**: Configurable `HASS_namespace` and `MQTT_namespace` for compatibility with custom setups.  
---

## 📱 Supported Platforms  
This app is designed for use with:  
- **[Home Assistant](https://www.home-assistant.io/)**: A popular open-source home automation platform.  
- **[AppDaemon](https://github.com/AppDaemon/appdaemon)**: A Python execution environment for writing automation apps.  
---

## 🛠️ Installation  
1. **Clone the repository** into your AppDaemon `apps` directory:

   ```bash
   git clone https://github.com/Pythm/ad-Weather.git /path/to/appdaemon/apps/
   ```  

2. **Add to your AppDaemon configuration** (`apps.yaml` or `apps.toml`)

```yaml
   weather:
     module: weather
     class: Weather
     weather: weather.forecast_home
     outside_temperature: sensor.outtemp
     outside_temperature_2: sensor.outtemp2
     outside_temperature_MQTT: zigbee2mqtt/outdoor_hue_lux
     outside_temperature_MQTT_2: zigbee2mqtt/outdoor_hue_lux_2
     OutLux_sensor: sensor.outdoor_hue_lux_illuminance
     OutLux_sensor_2: sensor.outdoor_hue_lux_illuminance_2
     OutLuxMQTT: zigbee2mqtt/outdoor_hue_lux
     OutLuxMQTT_2: zigbee2mqtt/outdoor_hue_lux_2
     rain_sensor: sensor.rain
     anemometer: sensor.wind
     HASS_namespace: default
     MQTT_namespace: mqtt
```  
---

## 🔄 How It Works  
This app acts as a **"helper"** to other apps by listening to weather sensor updates and publishing a `WEATHER_CHANGE` event with the latest data.  

To listen for weather updates in your AppDaemon app:  
```python
self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE')
```  
---


---

## 🔧 Configuration Parameters

| Key | Type | Default | Description |
| --- | ---- | ------- | ----------- |
| `weather` | string | *None* | HA `weather` entity (e.g. `weather.forecast_home`). If omitted, the first `weather.*` entity with a temperature is used. The chosen entity is logged at startup. It is the fallback when no sensor reports. |
| `outside_temperature` | string | *None* | Primary outdoor temperature sensor (HA). |
| `outside_temperature_2` | string | *None* | Secondary outdoor temperature sensor. The **lowest** fresh value is used. |
| `outside_temperature_MQTT` | string | *None* | MQTT topic with temperature. A JSON payload **must** contain the key `temperature`, otherwise the message is ignored. |
| `outside_temperature_MQTT_2` | string | *None* | Secondary MQTT temperature topic. |
| `OutLux_sensor` | string | *None* | HA lux sensor (e.g. `sensor.outdoor_lux`). |
| `OutLux_sensor_2` | string | *None* | Secondary lux sensor. The **highest** fresh value is used. |
| `OutLuxMQTT` | string | *None* | MQTT topic with lux (`illuminance` for Zigbee, `value` for Z-Wave, or a plain number). |
| `OutLuxMQTT_2` | string | *None* | Secondary MQTT lux topic. |
| `rain_sensor` | string | *None* | Rain sensor. |
| `anemometer` | string | *None* | Wind speed sensor. Its `unit_of_measurement` sets the wind unit of the event. |
| `estimate_lux` | bool | `false` | Estimate lux from sun elevation and cloud cover when **no** lux sensor is configured. A rough estimate. |
| `sun_entity` | string | `sun.sun` | Sun entity used by `estimate_lux`. |
| `HASS_namespace` | string | `"default"` | Home Assistant namespace. |
| `MQTT_namespace` | string | `"mqtt"` | MQTT namespace. |

> **Tip** - For any sensor you only need to specify *one* source. For redundancy add a second sensor ending with `_2`.

---

## 📤 The `WEATHER_CHANGE` event

Fired on the `HASS_namespace` when the data changed, at most once every 3 minutes. A change inside that window is sent when the window ends, so no change is lost. The event is **not** sent at startup: MQTT sensors only send data when they change, so the first event is sent when the first data is known.

| Key | Type | Description |
| --- | ---- | ----------- |
| `temp` | float or `None` | Outdoor temperature. |
| `rain` | float or `None` | Rain amount from the sensor. From the weather entity it is `1.0` when it rains or snows, otherwise `0.0`. |
| `wind` | float or `None` | Wind speed in `wind_unit`. |
| `wind_unit` | string | Unit of an `anemometer` sensor (`m/s`, `km/h`, `mph`, `kn`, `ft/s`). `km/h` if there is no anemometer. Weather entity wind speed is converted to this unit. |
| `lux` | float or `None` | Outdoor lux. |
| `cloud_cover` | int or `None` | Cloud coverage in percent, from the weather entity. |

**`None` means the value is not available** (no sensor and no weather entity provides it), it does not mean zero. Apps listening to the event must handle `None`.

```python
def weather_event(self, event_name, data, **kwargs):
    if data.get('temp') is not None:
        ...
```

---

## ⏱️ Sensor staleness and how values are chosen

| Value | Timeout | Used |
| ----- | ------- | ---- |
| Temperature | 20 min | **Lowest** of the fresh sensors |
| Lux | 15 min | **Highest** of the fresh sensors |
| Rain / Wind | 20 min | The sensor |

- The result is calculated from the stored value of every sensor each time, so it follows a sensor both up and down and does not depend on which sensor reported last.
- A Home Assistant sensor is fresh as long as `last_reported` (or `last_updated`) is within the timeout, so a sensor that holds the same value is **not** treated as stale. MQTT sources are fresh when a message arrived within the timeout.
- When no temperature, rain or wind sensor is fresh, the weather entity is used. Lux has no weather entity fallback: the last value is kept until a sensor reports, or `estimate_lux` is used if no lux sensor is configured.
- Missing `wind_speed` or `cloud_coverage` on the weather entity only leaves that value `None`.

---

## 📌 License  
[MIT License](https://github.com/Pythm/ad-Weather/blob/main/LICENSE)  

---

## 🤝 Contributing

Feel free to open issues or pull requests.  
Pull‑request guidelines:

1. Fork the repo and create a branch for your feature/bug‑fix.
2. Write or update tests (if applicable).
3. Ensure the README stays up‑to‑date.
4. Submit a pull request.

---

**ad‑Weather** by [Pythm](https://github.com/Pythm)  
[GitHub repository](https://github.com/Pythm/ad-Weather) |  
[Issues & PRs](https://github.com/Pythm/ad-Weather/issues)

---
