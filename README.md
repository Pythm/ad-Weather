
# ad-Weather  
**An AppDaemon app that centralises all outdoor weather data and publishes a single `WEATHER_CHANGE` event that can be consumed by any other AppDaemon apps.**  
---

## 🌍 Features  
- **Publishes `WEATHER_CHANGE` event**: Updates other AppDaemon apps with weather data (e.g., temperature, rain, wind, lux) when sensors change.  
- **Multi‑sensor support**: Up to two temperature and lux sensors for accurate outdoor temperature and lux tracking.
- **Home Assistant or MQTT sensors**: For lux and temperature you can use a combination of HA and MQTT sensors.
- **Fallback to Met.no integration**: Automatically detects a `weather` entity from Home Assistant if no explicit `weather` sensor is provided.
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
| `weather` | string | *None* | HA `weather` entity (e.g. `weather.forecast_home`).  If omitted, the app looks for any HA weather entity or falls back to Met.no. |
| `outside_temperature` | string | *None* | Primary outdoor temperature sensor (HA). |
| `outside_temperature_2` | string | *None* | Secondary outdoor temperature sensor. The app keeps the **lower** value when both are fresh. |
| `outside_temperature_MQTT` | string | *None* | MQTT topic that publishes temperature. |
| `outside_temperature_MQTT_2` | string | *None* | Secondary MQTT temperature topic. |
| `OutLux_sensor` | string | *None* | HA lux sensor (e.g. `sensor.outdoor_lux`). |
| `OutLux_sensor_2` | string | *None* | Secondary lux sensor. The app keeps the **higher** value when both are fresh. |
| `OutLuxMQTT` | string | *None* | MQTT topic that publishes lux. |
| `OutLuxMQTT_2` | string | *None* | Secondary MQTT lux topic. |
| `rain_sensor` | string | *None* | Rain sensor. |
| `anemometer` | string | *None* | Wind speed sensor. |
| `HASS_namespace` | string | `"default"` | Home Assistant namespace. |
| `MQTT_namespace` | string | `"mqtt"` | MQTT namespace. |

> **Tip** – For any sensor you only need to specify *one* source.  
> If you want redundancy, add a second sensor ending with `_2`.  
> The app automatically discards stale data (see below).

---

## ⏱️ Sensor staleness

| Sensor type | Timeout | When is it ignored? |
| ----------- | ------- | ------------------- |
| Temperature / Rain / Wind | 20 min | If older than this, the value is considered stale and will be replaced by another source. |
| Lux | 15 min | Same as above. |

When both sources are fresh, the temperature sensor will keep the **lower** of the two values (e.g. a sensor in shade).  
For lux, the **higher** value is kept (e.g. a sensor in full sun).  

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
