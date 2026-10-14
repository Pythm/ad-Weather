""" Weather sensors

    Collects outdoor weather data from Home Assistant sensors, MQTT topics and a
    weather entity, and publishes one WEATHER_CHANGE event for other apps.

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad
from datetime import timedelta
import json
import math

TEMP_STALE_MINUTES  = 20
LUX_STALE_MINUTES   = 15
EVENT_THROTTLE_MIN  = 3
REFRESH_SECONDS     = 300

# Wind speed units converted to m/s
WIND_TO_MS = {
    'm/s': 1.0,
    'km/h': 1 / 3.6,
    'mph': 0.44704,
    'kn': 0.514444,
    'knots': 0.514444,
    'ft/s': 0.3048,
}
DEFAULT_WIND_UNIT = 'km/h'


class Weather(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace = self.args.get('MQTT_namespace', 'mqtt')

        self.mqtt = None
        now = self.ADapi.datetime(aware=True)

            # Sources. A source is {'value': float|None, 'ts': datetime|None, 'entity': str|None}.
            # 'entity' is set for Home Assistant sensors, so last_reported can be used as freshness.
            # MQTT sources only get data when a message arrives.
        self.temp_sources:dict = {}
        self.lux_sources:dict = {}
        self.rain_source:dict = self._new_source()
        self.wind_source:dict = self._new_source()

            # Weather entity (fallback)
        self.weather_sensor = self.args.get('weather', None)
        self.weather_values:dict = {
            'temp': None, 'rain': None, 'wind': None, 'wind_unit': None, 'cloud_cover': None,
        }

            # Wind unit used in the event: unit of the anemometer if it has one, else km/h
        self.wind_unit:str = DEFAULT_WIND_UNIT

        self.estimate_lux:bool = bool(self.args.get('estimate_lux', False))
        self.sun_entity = self.args.get('sun_entity', 'sun.sun')

            # Event state
        self.last_sent:dict|None = None
        self.last_sent_time = now - timedelta(minutes = EVENT_THROTTLE_MIN)
        self.send_handle = None
        self.last_temp:float|None = None
        self.last_lux:float|None = None

            # Temperature sources
        for key, ha_key, mqtt_key in (
            ('temp1', 'outside_temperature', 'outside_temperature_MQTT'),
            ('temp2', 'outside_temperature_2', 'outside_temperature_MQTT_2'),
        ):
            self.temp_sources[key] = self._new_source()
            self._setup_source(
                self.temp_sources[key], key,
                self.args.get(ha_key), self.args.get(mqtt_key),
                self._temp_state_updated, self._temp_mqtt_event,
            )

            # Lux sources
        for key, ha_key, mqtt_key in (
            ('lux1', 'OutLux_sensor', 'OutLuxMQTT'),
            ('lux2', 'OutLux_sensor_2', 'OutLuxMQTT_2'),
        ):
            self.lux_sources[key] = self._new_source()
            self._setup_source(
                self.lux_sources[key], key,
                self.args.get(ha_key), self.args.get(mqtt_key),
                self._lux_state_updated, self._lux_mqtt_event,
            )

            # Rain and wind (Home Assistant sensors only)
        if (rain_sensor := self.args.get('rain_sensor')):
            self.rain_source['entity'] = rain_sensor
            self.ADapi.listen_state(self._rain_updated, rain_sensor,
                namespace = self.HASS_namespace
            )
            self._read_initial(self.rain_source)

        if (anemometer := self.args.get('anemometer')):
            self.wind_source['entity'] = anemometer
            self.ADapi.listen_state(self._wind_updated, anemometer,
                namespace = self.HASS_namespace
            )
            self._read_initial(self.wind_source)
            unit = self.ADapi.get_state(anemometer,
                attribute = 'unit_of_measurement',
                namespace = self.HASS_namespace
            )
            if isinstance(unit, str) and unit.strip().lower() in WIND_TO_MS:
                self.wind_unit = unit.strip().lower()

            # Weather entity
        self._setup_weather_entity()

            # Source ages and the estimate are re-evaluated even if no sensor reports
        self.ADapi.run_every(self._refresh, 'now+60', REFRESH_SECONDS)


    # ------------------------------------------------------------------ setup

    @staticmethod
    def _new_source() -> dict:
        return {'value': None, 'ts': None, 'entity': None}

    def _setup_source(self, source, name, ha_entity, mqtt_topic, state_cb, mqtt_cb) -> None:
        """ Registers listeners for one Home Assistant sensor and/or one MQTT topic.
            Both feed the same source slot, a source normally uses only one of them. """
        source['configured'] = bool(ha_entity or mqtt_topic)
        if ha_entity:
            source['entity'] = ha_entity
            self.ADapi.listen_state(state_cb, ha_entity,
                source = name,
                namespace = self.HASS_namespace
            )
            self._read_initial(source)

        if mqtt_topic:
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")
            self.mqtt.mqtt_subscribe(mqtt_topic)
            self.mqtt.listen_event(mqtt_cb, "MQTT_MESSAGE",
                topic = mqtt_topic,
                source = name,
                namespace = self.MQTT_namespace
            )

    def _read_initial(self, source) -> None:
        """ Reads the current value of a Home Assistant sensor. A MQTT topic has no state to read. """
        entity = source['entity']
        value = self._to_float(self.ADapi.get_state(entity, namespace = self.HASS_namespace))
        if value is None:
            return
        source['value'] = value
        source['ts'] = self._entity_timestamp(entity) or self.ADapi.datetime(aware=True)

    def _setup_weather_entity(self) -> None:
        if self.weather_sensor is None:
            states = self.ADapi.get_state(entity = 'weather', namespace = self.HASS_namespace)
            if isinstance(states, dict):
                for sensor_id, state in sorted(states.items()):
                    if not sensor_id.startswith('weather.') or not isinstance(state, dict):
                        continue
                    if self._to_float(state.get('attributes', {}).get('temperature')) is not None:
                        self.weather_sensor = sensor_id
                        break

        if not self.weather_sensor:
            self.ADapi.log(
                "No weather entity found. Weather data comes from the configured sensors only. "
                "Use https://www.home-assistant.io/integrations/met/ or set 'weather' in the configuration.",
                level = 'INFO'
            )
            return

        self.ADapi.log(f"Using weather entity {self.weather_sensor} as fallback.", level = 'INFO')
        self.ADapi.listen_state(self._weather_entity_updated, self.weather_sensor,
            attribute = 'all',
            namespace = self.HASS_namespace
        )
        self._read_weather_entity(self.ADapi.get_state(self.weather_sensor,
            attribute = 'all',
            namespace = self.HASS_namespace
        ))

    # ---------------------------------------------------------------- helpers

    @staticmethod
    def _to_float(value) -> float|None:
        try:
            result = float(value)
        except (ValueError, TypeError):
            return None
        return result if math.isfinite(result) else None

    def _entity_timestamp(self, entity):
        """ Latest time Home Assistant got a value from the sensor, even if the value was unchanged. """
        for attr in ('last_reported', 'last_updated'):
            raw = self.ADapi.get_state(entity, attribute = attr, namespace = self.HASS_namespace)
            if raw:
                try:
                    return self.ADapi.convert_utc(raw)
                except (ValueError, TypeError):
                    continue
        return None

    def _is_fresh(self, source, minutes) -> bool:
        if source['value'] is None or source['ts'] is None:
            return False
        ts = source['ts']
        if source['entity']:
            reported = self._entity_timestamp(source['entity'])
            if reported is not None and reported > ts:
                ts = reported
        return self.ADapi.datetime(aware=True) - ts <= timedelta(minutes = minutes)

    def _store(self, source, value) -> None:
        source['value'] = value
        source['ts'] = self.ADapi.datetime(aware=True)

    def _parse_mqtt(self, data, keys) -> float|None:
        """ Payload is a number, or a JSON object where one of 'keys' holds the number. """
        payload = data.get('payload')
        if isinstance(payload, bytes):
            try:
                payload = payload.decode()
            except UnicodeDecodeError:
                return None
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            pass
        if isinstance(payload, dict):
            for key in keys:
                if key in payload:
                    return self._to_float(payload[key])
            return None
        return self._to_float(payload)

    # ------------------------------------------------------------- listeners

    def _temp_state_updated(self, entity, attribute, old, new, kwargs) -> None:
        source = self.temp_sources[kwargs['source']]
        value = self._to_float(new)
        if value is None:
            source['value'] = None
            return
        self._store(source, value)
        self._publish()

    def _temp_mqtt_event(self, event_name, data, kwargs) -> None:
        value = self._parse_mqtt(data, ('temperature',))
        if value is None:
            return
        self._store(self.temp_sources[kwargs['source']], value)
        self._publish()

    def _lux_state_updated(self, entity, attribute, old, new, kwargs) -> None:
        source = self.lux_sources[kwargs['source']]
        value = self._to_float(new)
        if value is None:
            source['value'] = None
            return
        self._store(source, value)
        self._publish()

    def _lux_mqtt_event(self, event_name, data, kwargs) -> None:
        # Zigbee sensors send 'illuminance', Z-Wave sensors send 'value'
        value = self._parse_mqtt(data, ('illuminance', 'value'))
        if value is None:
            return
        self._store(self.lux_sources[kwargs['source']], value)
        self._publish()

    def _rain_updated(self, entity, attribute, old, new, kwargs) -> None:
        value = self._to_float(new)
        if value is None:
            self.rain_source['value'] = None
            return
        self._store(self.rain_source, value)
        self._publish()

    def _wind_updated(self, entity, attribute, old, new, kwargs) -> None:
        value = self._to_float(new)
        if value is None:
            self.wind_source['value'] = None
            return
        self._store(self.wind_source, value)
        self._publish()

    def _weather_entity_updated(self, entity, attribute, old, new, kwargs) -> None:
        self._read_weather_entity(new)
        self._publish()

    def _read_weather_entity(self, state) -> None:
        """ Reads the weather entity. Missing attributes only leave that value empty. """
        if not isinstance(state, dict):
            return
        attributes = state.get('attributes') or {}
        condition = state.get('state')
        if condition in ('unavailable', 'unknown', None):
            self.weather_values.update(temp = None, rain = None, wind = None, cloud_cover = None)
            return

        wind = self._to_float(attributes.get('wind_speed'))
        if wind is not None:
            wind = self._convert_wind(wind, attributes.get('wind_speed_unit'))
        cloud = self._to_float(attributes.get('cloud_coverage'))

        self.weather_values.update(
            temp = self._to_float(attributes.get('temperature')),
            # The weather entity has no rain amount, only a condition
            rain = 1.0 if condition in ('snowy', 'rainy', 'rainy_snowy', 'pouring', 'lightning-rainy', 'snowy-rainy') else 0.0,
            wind = wind,
            cloud_cover = int(cloud) if cloud is not None else None,
        )

    def _convert_wind(self, value, from_unit) -> float:
        """ Converts a wind speed from the weather entity to the unit used in the event. """
        source_unit = from_unit.strip().lower() if isinstance(from_unit, str) else DEFAULT_WIND_UNIT
        if source_unit not in WIND_TO_MS:
            return value
        return value * WIND_TO_MS[source_unit] / WIND_TO_MS[self.wind_unit]

    # ------------------------------------------------------------ calculation

    def _estimate_lux(self) -> float|None:
        """ Rough outdoor lux from sun elevation and cloud cover, only if estimate_lux is set. """
        elevation = self._to_float(self.ADapi.get_state(self.sun_entity,
            attribute = 'elevation',
            namespace = self.HASS_namespace
        ))
        if elevation is None:
            return None
        if elevation <= 0:
            return 0.0
        clear_sky = 110000 * math.sin(math.radians(elevation))
        cloud = self.weather_values['cloud_cover']
        if cloud is None:
            return round(clear_sky * 0.5, 0)
        factor = 1 - 0.75 * (min(max(cloud, 0), 100) / 100) ** 3.4
        return round(clear_sky * factor, 0)

    def _calculate(self) -> dict:
        """ Builds the event data from the current sources.
            Temperature uses the LOWEST fresh value and lux the HIGHEST fresh value, by design.
            The result is computed from all stored values every time, so it follows a sensor
            in both directions and does not depend on which sensor reported last. """

        temps = [s['value'] for s in self.temp_sources.values() if self._is_fresh(s, TEMP_STALE_MINUTES)]
        if temps:
            temp = min(temps)
        elif self.weather_values['temp'] is not None:
            temp = self.weather_values['temp']
        else:
            temp = self.last_temp
        self.last_temp = temp

        lux_configured = any(s.get('configured') for s in self.lux_sources.values())
        luxes = [s['value'] for s in self.lux_sources.values() if self._is_fresh(s, LUX_STALE_MINUTES)]
        if luxes:
            lux = max(luxes)
        elif not lux_configured and self.estimate_lux:
            lux = self._estimate_lux()
        else:
            # Sensors only report changes: keep the last value until a sensor reports again
            lux = self.last_lux
        self.last_lux = lux

        if self.rain_source['entity']:
            rain = self.rain_source['value'] if self._is_fresh(self.rain_source, TEMP_STALE_MINUTES) else None
        else:
            rain = None
        if rain is None:
            rain = self.weather_values['rain']

        if self.wind_source['entity']:
            wind = self.wind_source['value'] if self._is_fresh(self.wind_source, TEMP_STALE_MINUTES) else None
        else:
            wind = None
        if wind is None:
            wind = self.weather_values['wind']

        return {
            'temp': temp,
            'rain': rain,
            'wind': wind,
            'lux': lux,
            'cloud_cover': self.weather_values['cloud_cover'],
            'wind_unit': self.wind_unit,
        }

    # ---------------------------------------------------------------- publish

    def _refresh(self, **kwargs) -> None:
        self._publish()

    def _publish(self) -> None:
        """ Sends the event if data changed. Inside the throttle window the newest data is sent
            by a timer when the window ends, so a change is never lost. """
        data = self._calculate()
        if data == self.last_sent:
            return
        if self.last_sent is None and all(v is None for k, v in data.items() if k != 'wind_unit'):
            return  # Nothing known yet
        if self.send_handle is not None and self.ADapi.timer_running(self.send_handle):
            return  # The pending timer calculates fresh data when it runs

        wait = timedelta(minutes = EVENT_THROTTLE_MIN) - (self.ADapi.datetime(aware=True) - self.last_sent_time)
        if wait.total_seconds() > 0:
            self.send_handle = self.ADapi.run_in(self._send_pending, wait.total_seconds() + 1)
            return
        self._send(data)

    def _send_pending(self, **kwargs) -> None:
        self.send_handle = None
        data = self._calculate()
        if data != self.last_sent:
            self._send(data)

    def _send(self, data) -> None:
        self.ADapi.fire_event('WEATHER_CHANGE',
            namespace = self.HASS_namespace,
            **data
        )
        self.last_sent = data
        self.last_sent_time = self.ADapi.datetime(aware=True)

    def getOutTemp(self) -> float|None:
        """ Returns outdoor temperature """
        return self._calculate()['temp']
