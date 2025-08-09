
# ad-Weather  
**An AppDaemon weather app that publishes a `WEATHER_CHANGE` event with valid data upon sensor updates to other AppDaemon apps.**  
---

## 🌍 Features  
- **Publishes `WEATHER_CHANGE` event**: Updates other AppDaemon apps with weather data (e.g., temperature, rain, wind, lux) when sensors change.  
- **Supports multiple weather sensors**: Uses `outside_temperature` and `outside_temperature_2` for accurate outdoor temperature tracking.  
- **Lux sensor integration**: Supports up to **two outdoor lux sensors** (e.g., `OutLux_sensor` and `OutLuxMQTT_2`) to determine the highest lux value.  
- **Fallback to Met.no integration**: Automatically detects weather data from Home Assistant if no explicit `weather` sensor is provided.  
- **Namespace flexibility**: Configurable `HASS_namespace` and `MQTT_namespace` for compatibility with custom setups.  
- **Used by other apps**: Powers [ad-ClimateCommander](https://github.com/Pythm/ad-ClimateCommander) and [ad-ElectricalManagement](https://github.com/Pythm/ad-ElectricalManagement) for weather-dependent automation.  
---

## 📱 Supported Platforms  
This app is designed for use with:  
- **[Home Assistant](https://www.home-assistant.io/)**: A popular open-source home automation platform.  
- **[AppDaemon](https://github.com/AppDaemon/appdaemon)**: A Python execution environment for writing automation apps.  
---

## 🔄 How It Works  
This app acts as a **"helper"** to other apps by listening to weather sensor updates and publishing a `WEATHER_CHANGE` event with the latest data.  

To listen for weather updates in your AppDaemon app:  
```python
self.ADapi.listen_event(self.weather_event, 'WEATHER_CHANGE', namespace=self.HASS_namespace)
```  
---

## 🛠️ Installation  
1. **Clone the repository** into your AppDaemon `apps` directory:  
   ```bash
   git clone https://github.com/Pythm/ad-Weather.git /path/to/appdaemon/apps/
   ```  
2. **Add configuration** to a `.yaml` or `.toml` file:  
   ```yaml
   weather:
     module: weather
     class: Weather
     weather: weather.forecast_home
     outside_temperature: sensor.outtemp
     outside_temperature_2: sensor.outtemp2
     rain_sensor: sensor.rain
     anemometer: sensor.wind
     OutLux_sensor: sensor.lux
     OutLuxMQTT_2: zigbee2mqtt/OutdoorHueLux
     HASS_namespace: default
     MQTT_namespace: mqtt
   ```  
---

## 📌 Configuration Details  
### Key Definitions  
| Key                      | Type   | Default         | Description                                                                 |
|--------------------------|--------|------------------|-----------------------------------------------------------------------------|
| `weather`                | string | (optional)       | Home Assistant weather sensor or Met.no integration.                      |
| `outside_temperature`    | string | (optional)       | Primary outdoor temperature sensor.                                         |
| `outside_temperature_2`  | string | (optional)       | Secondary outdoor temperature sensor.                                       |
| `rain_sensor`            | string | (optional)       | Sensor to detect rain (state: `snowy`, `rainy`, `rainy_snowy`).            |
| `anemometer`             | string | (optional)       | Wind speed sensor.                                                          |
| `OutLux_sensor`          | string | (optional)       | Home Assistant outdoor lux sensor.                                         |
| `OutLuxMQTT`             | string | (optional)       | MQTT outdoor lux sensor.                                                   |
| `HASS_namespace`         | string | `"default"`      | Home Assistant namespace (optional).                                        |
| `MQTT_namespace`         | string | `"mqtt"`         | MQTT namespace (optional).                                                  |

> ⚠️ Note: Only **two** lux sensors are supported but a combination of HA and MQTT is possible. The second sensor must end with `_2`.  

---

## 📌 Tips & Best Practices  
- **Use multiple sensors**: Configure a second `outside_temperature`, `OutLux_sensor`, or `OutLuxMQTT_2` ending with `_2` for redundancy and accuracy.  
- **Fallback to Met.no**: If no `weather` sensor is defined, the app will attempt to find a `weather` sensor in Home Assistant.  
- **Rain detection**: The app assumes a rain amount of `1.0` if the `rain_sensor` state is `snowy`, `rainy`, or `rainy_snowy`.  
- **Lux sensor behavior**: The app retains the last updated value if one of the sensors hasn’t updated in 15 minutes.  
- **Namespace configuration**: Explicitly define `HASS_namespace` and `MQTT_namespace` if you’re using custom namespaces.  

---

## 📈 Roadmap  
- Add support for MQTT temperature sensors

---

## 📌 License  
[MIT License](https://github.com/Pythm/ad-Weather/blob/main/LICENSE)  

---

## 🙋 Contributing  
Found a bug or want to suggest a feature? [Open an issue](https://github.com/Pythm/ad-Weather/issues) or [submit a PR](https://github.com/Pythm/ad-Weather/pulls).  

---

**ad-Weather by [Pythm](https://github.com/Pythm)**  
[GitHub](https://github.com/Pythm/ad-Weather)

---  
**Need further assistance?** Reach out on [GitHub](https://github.com/Pythm/ad-Weather).  

---
