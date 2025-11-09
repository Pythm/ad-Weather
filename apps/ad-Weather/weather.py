""" Weather sensors

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.2.0"

from appdaemon import adbase as ad
from datetime import timedelta
import json

TEMP_STALE_MINUTES  = 20
LUX_STALE_MINUTES   = 15
EVENT_THROTTLE_MIN  = 3

class Weather(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace = self.args.get('MQTT_namespace', 'mqtt')

        self.mqtt = None
        now = self.ADapi.datetime(aware=True)

            # Current Weather Values
        self.out_temp:float = 10.0
        self.out_temp_1:float = 10.0
        self.out_temp_2:float = 10.0
        self.out_temp_1_last_update = now - timedelta(minutes = TEMP_STALE_MINUTES)
        self.out_temp_2_last_update = now - timedelta(minutes = TEMP_STALE_MINUTES)

        self.rain_amount:float = 0.0
        self.rain_last_update = now - timedelta(minutes = TEMP_STALE_MINUTES)
        self.wind_amount:float = 0.0
        self.wind_last_update = now - timedelta(minutes = TEMP_STALE_MINUTES)

        self.out_lux:float = 0.0
        self.out_lux_1:float = 0.0
        self.out_lux_2:float = 0.0
        self.out_lux_1_last_update = now - timedelta(minutes = LUX_STALE_MINUTES)
        self.out_lux_2_last_update = now - timedelta(minutes = LUX_STALE_MINUTES)
        self.cloud_cover:int = 0

        self.weather_event_last_update = now - timedelta(minutes = EVENT_THROTTLE_MIN)

            # Weather sensors
        self.weather_sensor = self.args.get('weather', None)

            # Setup Weater sensors
        if self.weather_sensor is None:
            sensor_states = self.ADapi.get_state(entity='weather', namespace = self.HASS_namespace)
            for sensor_id, sensor_states in sensor_states.items():
                if 'weather.' in sensor_id:
                    try:
                        self.out_temp = float(self.ADapi.get_state(sensor_id,
                            attribute = 'temperature',
                            namespace = self.HASS_namespace
                        ))
                    except Exception:
                        pass
                    else:
                        self.weather_sensor = sensor_id
                        break

        if self.weather_sensor:
            self.ADapi.listen_state(self.WeatherSensorUpdated, self.weather_sensor,
                attribute = 'temperature',
                namespace = self.HASS_namespace
            )
            try:
                self.out_temp = float(self.ADapi.get_state(self.weather_sensor,
                    attribute = 'temperature',
                    namespace = self.HASS_namespace
                ))
            except Exception as err:
                self.ADapi.log(
                    f"Was not able to get temperature from {self.weather_sensor}. "
                    f"Please use https://www.home-assistant.io/integrations/met/ or make a pull requeset to support other integrations. {err}",
                    level = 'INFO'
                )

        if (out_temp_sensor := self.args.get('outside_temperature')):
            self.ADapi.listen_state(self._out_temp_updated, out_temp_sensor,
                namespace = self.HASS_namespace
            )
            try:
                self.out_temp = float(self.ADapi.get_state(out_temp_sensor,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError) as ve:
                pass

        if (out_temp_sensor := self.args.get('outside_temperature_MQTT')):
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")

            self.mqtt.mqtt_subscribe(out_temp_sensor)
            self.mqtt.listen_event(self._out_temp_mqtt_event, "MQTT_MESSAGE",
                topic = out_temp_sensor,
                namespace = self.MQTT_namespace
            )

        if (out_temp_sensor_2 := self.args.get('outside_temperature_2')):
                self.ADapi.listen_state(self._out_temp_2_updated, out_temp_sensor_2,
                    namespace = self.HASS_namespace
                )

        if (out_temp_sensor_2 := self.args.get('outside_temperature_MQTT_2')):
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")

            self.mqtt.mqtt_subscribe(out_temp_sensor_2)
            self.mqtt.listen_event(self._out_temp_2_mqtt_event, "MQTT_MESSAGE",
                topic = out_temp_sensor_2,
                namespace = self.MQTT_namespace
            )

            # Setup Rain sensor
        if (rain_sensor := self.args.get('rain_sensor')):
            self.ADapi.listen_state(self._rain_amount_updated, rain_sensor,
                namespace = self.HASS_namespace
            )
            try:
                self.rain_amount = float(self.ADapi.get_state(rain_sensor,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError):
                pass

            # Setup Wind sensor
        if (anemometer := self.args.get('anemometer')):
            self.ADapi.listen_state(self._wind_amount_updated, anemometer,
                namespace = self.HASS_namespace
            )
            try:
                self.wind_amount = float(self.ADapi.get_state(anemometer,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError):
                pass

            # Setup Outdoor Lux sensor
        if (lux_sensor := self.args.get('OutLux_sensor')):
            self.ADapi.listen_state(self._out_lux_updated, lux_sensor,
                namespace = self.HASS_namespace
            )
            try:
                self.out_lux = float(self.ADapi.get_state(lux_sensor,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError):
                pass

        if (lux_sensor := self.args.get('OutLuxMQTT')):
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")

            self.mqtt.mqtt_subscribe(lux_sensor)
            self.mqtt.listen_event(self._out_lux_mqtt_event, "MQTT_MESSAGE",
                topic = lux_sensor,
                namespace = self.MQTT_namespace
            )

        if (lux_sensor_2 := self.args.get('OutLux_sensor_2')):
            self.ADapi.listen_state(self._out_lux_2_updated, lux_sensor_2,
                namespace = self.HASS_namespace
            )

        if (lux_sensor_2 := self.args.get('OutLuxMQTT_2')):
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")

            self.mqtt.mqtt_subscribe(lux_sensor_2)
            self.mqtt.listen_event(self._out_lux_2_mqtt_event, "MQTT_MESSAGE",
                topic = lux_sensor_2,
                namespace = self.MQTT_namespace
            )


    def send_weather_update(self, force: bool = False) -> None:
        """Sends a new event with updated sensor data"""

        now = self.ADapi.datetime(aware=True)
        if force or now - self.weather_event_last_update > timedelta(minutes=EVENT_THROTTLE_MIN):
            self.ADapi.fire_event(
                'WEATHER_CHANGE',
                temp=float(self.out_temp),
                rain=float(self.rain_amount),
                wind=float(self.wind_amount),
                lux=float(self.out_lux),
                cloud_cover=int(self.cloud_cover),
                namespace=self.HASS_namespace
            )
            self.weather_event_last_update = now

        # Set proper value when weather sensors is updated
    def _out_temp_updated(self, entity, attribute, old, new, kwargs) -> None:
        now = self.ADapi.datetime(aware=True)
        try:
            temp = float(new)
        except (ValueError, TypeError):
            return
        self.out_temp_1 = temp
        self._choose_temperature(
            new=temp,
            other=self.out_temp_2,
            other_last=self.out_temp_2_last_update,
        )
        self.out_temp_1_last_update = now

    def _out_temp_mqtt_event(self, event_name, data, **kwargs) -> None:
        self._handle_mqtt_temp(data, attr='out_temp_1')

    def _out_temp_2_updated(self, entity, attribute, old, new, kwargs) -> None:
        now = self.ADapi.datetime(aware=True)
        try:
            temp = float(new)
        except (ValueError, TypeError):
            return
        self.out_temp_2 = temp
        self._choose_temperature(
            new=temp,
            other=self.out_temp_1,
            other_last=self.out_temp_1_last_update,
        )
        self.out_temp_2_last_update = now

    def _out_temp_2_mqtt_event(self, event_name, data, **kwargs) -> None:
        self._handle_mqtt_temp(data, attr='out_temp_2')

    def WeatherSensorUpdated(self, entity, attribute, old, new, kwargs) -> None:
        weather_temp:float = 10.0
        weather_rain_amount:float = 0.0
        weather_wind_amount:float = 0.0

        state = self.ADapi.get_state(self.weather_sensor,
                    namespace = self.HASS_namespace
                )
        if state in ('snowy', 'rainy', 'rainy_snowy'):
            weather_rain_amount = 1.0
        else:
            weather_rain_amount = 0.0

        try:
            weather_temp = float(new)

            weather_wind_amount = float(self.ADapi.get_state(self.weather_sensor,
                                attribute = 'wind_speed',
                                namespace = self.HASS_namespace
                            ))

            self.cloud_cover = int(self.ADapi.get_state(self.weather_sensor,
                                attribute = 'cloud_coverage',
                                namespace = self.HASS_namespace
                            ))

        except (ValueError, TypeError):
            return

        now = self.ADapi.datetime(aware=True)
        if (
            now - self.out_temp_1_last_update > timedelta(minutes = TEMP_STALE_MINUTES)
            and now - self.out_temp_2_last_update > timedelta(minutes = TEMP_STALE_MINUTES)
        ):
            self.out_temp = weather_temp

        if now - self.rain_last_update > timedelta(minutes = TEMP_STALE_MINUTES):
            self.rain_amount = weather_rain_amount
        
        if now - self.wind_last_update > timedelta(minutes = TEMP_STALE_MINUTES):  
            self.wind_amount = weather_wind_amount

        self.send_weather_update()


    def _rain_amount_updated(self, entity, attribute, old, new, kwargs) -> None:
        try:
            self.rain_amount = float(new)
        except (ValueError, TypeError):
            return

        self.rain_last_update = self.ADapi.datetime(aware=True)
        self.send_weather_update()

    def _wind_amount_updated(self, entity, attribute, old, new, kwargs) -> None:
        try:
            self.wind_amount = float(new)
        except (ValueError, TypeError):
            return

        self.wind_last_update = self.ADapi.datetime(aware=True)
        self.send_weather_update()

        # Lux / weather
    def _out_lux_updated(self, entity, attribute, old, new, kwargs) -> None:
        try:
            value = float(new)
        except (ValueError, TypeError):
            return
        if value != self.out_lux_1:
            self._choose_lux(
                new=value,
                other=self.out_lux_2,
                other_last=self.out_lux_2_last_update,
            )
            self.out_lux_1 = value
            self.out_lux_1_last_update = self.ADapi.datetime(aware=True)

    def _out_lux_mqtt_event(self, event_name, data, **kwargs) -> None:
        self._handle_mqtt_lux(data, attr='out_lux_1')

    def _out_lux_2_updated(self, entity, attribute, old, new, kwargs) -> None:
        try:
            value = float(new)
        except (ValueError, TypeError):
            return
        if value != self.out_lux_2:
            self._choose_lux(
                new=value,
                other=self.out_lux_1,
                other_last=self.out_lux_1_last_update,
            )
            self.out_lux_2 = value
            self.out_lux_2_last_update = self.ADapi.datetime(aware=True)

    def _out_lux_2_mqtt_event(self, event_name, data, **kwargs) -> None:
        self._handle_mqtt_lux(data, attr='out_lux_2')

    def _handle_mqtt_temp(self, data, attr):
        payload = data.get('payload')
        if isinstance(payload, bytes):
            try:
                payload_json = payload.decode()
            except Exception:
                return

        try:
            payload_json = json.loads(payload)
        except Exception:
            payload_json = payload

        try:
            if isinstance(payload_json, dict):
                if 'temperature' in payload_json:
                    temp_val = float(payload_json['temperature'])
                else:
                    temp_val = float(next(v for v in payload_json.values()
                                        if isinstance(v, (int, float, str))))
            else:
                temp_val = float(payload_json)
        except Exception:
            return

        if temp_val != getattr(self, attr):
            setattr(self, attr, temp_val)
        now = self.ADapi.datetime(aware=True)
        if attr == 'out_temp_1':
            self._choose_temperature(
                new=temp_val,
                other=self.out_temp_2,
                other_last=self.out_temp_2_last_update,
            )
            self.out_temp_1_last_update = now
        else:
            self._choose_temperature(
                new=temp_val,
                other=self.out_temp_1,
                other_last=self.out_temp_1_last_update,
            )
            self.out_temp_2_last_update = now

    def _choose_temperature(self, new, other, other_last):
        now = self.ADapi.datetime(aware=True)
        if now - other_last > timedelta(minutes=TEMP_STALE_MINUTES) or new <= other:
            self.out_temp = new
            self.send_weather_update()

    def _handle_mqtt_lux(self, data, attr):
        payload = data.get('payload')
        if isinstance(payload, bytes):
            try:
                payload_json = payload.decode()
            except Exception:
                return

        try:
            payload_json = json.loads(payload)
        except Exception:
            payload_json = payload

        try:
            if isinstance(payload_json, dict):
                old_attr = getattr(self, attr)
                match payload_json:
                    case {'illuminance': illuminance} if old_attr != float(illuminance):
                        value = float(illuminance) # Zigbee sensor
                    case {'value': value} if old_attr != float(value):
                        value = float(value) # Zwave sensor
                    case _:
                        return
            else:
                value = float(payload_json)
        except Exception as e:
            return
        if value != getattr(self, attr):
            setattr(self, attr, value)
            now = self.ADapi.datetime(aware=True)
            if attr == 'out_lux_1':
                self._choose_lux(
                    new=value,
                    other=self.out_lux_2,
                    other_last=self.out_lux_2_last_update,
                )
                self.out_lux_1_last_update = now
            else:
                self._choose_lux(
                    new=value,
                    other=self.out_lux_1,
                    other_last=self.out_lux_1_last_update,
                )
                self.out_lux_2_last_update = now

    def _choose_lux(self, new, other, other_last):
        now = self.ADapi.datetime(aware=True)
        if now - other_last > timedelta(minutes=LUX_STALE_MINUTES) or new >= other:
            self.out_lux = new
            self.send_weather_update()


    def getOutTemp(self) -> float:
        """ Returns outdoor temperature """
        return self.out_temp
