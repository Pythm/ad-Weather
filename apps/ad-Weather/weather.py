""" Weather sensors

    @Pythm / https://github.com/Pythm
"""

__version__ = "0.1.1"

from appdaemon import adbase as ad
import datetime
import math
import json

class Weather(ad.ADBase):

    def initialize(self):

        self.ADapi = self.get_ad_api()
            # Namespaces
        self.HASS_namespace = self.args.get('HASS_namespace', 'default')
        self.MQTT_namespace = self.args.get('MQTT_namespace', 'default')
        self.mqtt = None

            # Current Weather Values
        self.out_temp:float = 10.0
        self.outTemp1:float = 10.0
        self.outTemp2:float = 10.0
        self.outTemp_last_update1 = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20) # Helpers for last updated when two outdoor lux sensors in use
        self.outTemp_last_update2 = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)

        self.rain_amount:float = 0.0
        self.rain_last_update = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)
        self.wind_amount:float = 0.0
        self.wind_last_update = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)

        self.out_lux:float = 0.0
        self.outLux1:float = 0.0
        self.outLux2:float = 0.0
        self.lux_last_update1 = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)
        self.lux_last_update2 = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)
        self.cloud_cover:int = 0

            # Weather sensors
        self.weather_sensor = self.args.get('weather', None)
        self.outside_temperature = None
        self.outside_temperature2 = None
        self.backup_temp_handler = None

        self.rain_sensor = self.args.get('rain_sensor', None)
        self.backup_rain_handler = None
        self.anemometer = self.args.get('anemometer', None)
        self.backup_wind_handler = None

        self.weather_event_last_update = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)

            # Setup Outside temperatures
        if self.weather_sensor is None:
            sensor_states = self.ADapi.get_state(entity='weather', namespace = self.HASS_namespace)
            for sensor_id, sensor_states in sensor_states.items():
                if 'weather.' in sensor_id:
                    self.weather_sensor = sensor_id
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
                    else:
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

        if 'outside_temperature' in self.args:
            self.outside_temperature = self.args['outside_temperature']
            self.ADapi.listen_state(self.outsideTemperatureUpdated, self.outside_temperature,
                namespace = self.HASS_namespace
            )
            try:
                self.out_temp = float(self.ADapi.get_state(self.outside_temperature,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError) as ve:
                self.ADapi.log(
                    f"Was not able to get temperature from {self.outside_temperature}. {ve}",
                    level = 'DEBUG'
                )
            except Exception as e:
                self.ADapi.log(f"Outside temperature is not valid. {e}", level = 'WARNING')

        if 'outside_temperature2' in self.args:
                self.outside_temperature2 = self.args['outside_temperature2']
                self.ADapi.listen_state(self.outsideTemperature2Updated, self.outside_temperature2,
                    namespace = self.HASS_namespace
                )

        # TODO: Add MQTT outdoor temperature sensor

            # Check if there are sensors to use
        if (
            self.outside_temperature is None 
            and self.weather_sensor is None
        ):
            self.ADapi.log(
                "Outside temperature not configured. Please provide sensors or install Met.no in Home Assistant. "
                "https://www.home-assistant.io/integrations/met/",
                level = 'WARNING'
            )
            self.ADapi.log("Aborting weather setup", level = 'WARNING')
            return


            # Setup Rain sensor
        if self.rain_sensor:
            self.ADapi.listen_state(self.rainSensorUpdated, self.rain_sensor,
                namespace = self.HASS_namespace
            )
            try:
                self.rain_amount = float(self.ADapi.get_state(self.rain_sensor,
                    namespace = self.HASS_namespace
                ))
            except (ValueError, TypeError) as ve:
                self.ADapi.log(
                    f"Was not able to get rain amount from {self.rain_sensor}. {ve}",
                    level = 'DEBUG'
                )
            except Exception as e:
                self.ADapi.log(f"Rain sensor not valid. {e}", level = 'WARNING')
                self.rain_amount = 0.0


            # Setup Wind sensor
        if self.anemometer:
            self.ADapi.listen_state(self.anemometerUpdated, self.anemometer,
                namespace = self.HASS_namespace
            )
            try:
                self.wind_amount = float(self.ADapi.get_state(self.anemometer,
                    namespace = self.HASS_namespace
                ))
            except ValueError as ve:
                self.ADapi.log(
                    f"Was not able to get wind_speed from {self.anemometer}. {ve}",
                    level = 'DEBUG'
                )

            except Exception as e:
                self.ADapi.log(f"Anemometer sensor not valid. {e}", level = 'WARNING')
                self.wind_amount = 0.0


            # Setup Outdoor Lux sensor
        if 'OutLux_sensor' in self.args:
            lux_sensor = self.args['OutLux_sensor']
            self.ADapi.listen_state(self.out_lux_state, lux_sensor,
                namespace = self.HASS_namespace
            )
            new_lux = self.ADapi.get_state(lux_sensor,
                namespace = self.HASS_namespace
            )
            try:
                self.out_lux = float(new_lux)
            except ValueError as ve:
                self.out_lux:float = 0.0
                self.ADapi.log(f"Not able to set Rain amount. Exception: {ve}", level = 'DEBUG')
            except Exception as e:
                self.out_lux:float = 0.0
                self.ADapi.log(f"Not able to set Rain amount. Exception: {e}", level = 'INFO')

        elif 'OutLuxMQTT' in self.args:
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")
            out_lux_sensor = self.args['OutLuxMQTT']
            self.mqtt.mqtt_subscribe(out_lux_sensor)
            self.mqtt.listen_event(self.out_lux_event_MQTT, "MQTT_MESSAGE",
                topic = out_lux_sensor,
                namespace = self.MQTT_namespace
            )

        if 'OutLux_sensor_2' in self.args:
            lux_sensor = self.args['OutLux_sensor_2']
            self.ADapi.listen_state(self.out_lux_state2, lux_sensor,
                namespace = self.HASS_namespace
            )
        elif 'OutLuxMQTT_2' in self.args:
            if not self.mqtt:
                self.mqtt = self.get_plugin_api("MQTT")
            out_lux_sensor = self.args['OutLuxMQTT_2']
            self.mqtt.mqtt_subscribe(out_lux_sensor)
            self.mqtt.listen_event(self.out_lux_event_MQTT2, "MQTT_MESSAGE",
                topic = out_lux_sensor,
                namespace = self.MQTT_namespace
            )


    def send_weather_update(self):
        """ Sends a new event with updated sensor data
        """
        if self.ADapi.datetime(aware=True) - self.weather_event_last_update > datetime.timedelta(minutes = 5):
            self.ADapi.fire_event('WEATHER_CHANGE',
                temp = self.out_temp,
                rain = self.rain_amount,
                wind = self.wind_amount,
                lux = self.out_lux,
                cloud_cover = self.cloud_cover,
                namespace = self.HASS_namespace
            )
            self.weather_event_last_update = self.ADapi.datetime(aware=True)


        # Set proper value when weather sensors is updated
    def outsideTemperatureUpdated(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates out temperature from sensor
        """
        try:
            self.outTemp1 = float(new)
        except (ValueError, TypeError) as ve:
            self.ADapi.log(
                f"Was not able to get temperature from {self.outside_temperature}. {ve}",
                level = 'DEBUG'
            )
        else:
            self.newOutTemp()


    def outsideTemperature2Updated(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates out temperature from sensor
        """
        try:
            self.outTemp2 = float(new)
        except (ValueError, TypeError) as ve:
            self.ADapi.log(
                f"Was not able to get temperature from {self.outside_temperature2}. {ve}",
                level = 'DEBUG'
            )
        else:
            self.newOutTemp2()


    def WeatherSensorUpdated(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates out temperature from backup sensor
        """
        weather_temp:float = 10.0
        weather_rain_amount:float = 0.0
        weather_wind_amount:float = 0.0

        state = self.ADapi.get_state(self.weather_sensor,
                    namespace = self.HASS_namespace
                )
        if state in ['snowy', 'rainy', 'rainy_snowy']:
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

        except TypeError as te:
            self.ADapi.log(f"Not able to get all values from {self.weather_sensor}. {te}", level = 'DEBUG')
        else:
            if (
                self.ADapi.datetime(aware=True) - self.outTemp_last_update1 > datetime.timedelta(minutes = 20)
                and self.ADapi.datetime(aware=True) - self.outTemp_last_update2 > datetime.timedelta(minutes = 20)
            ):
                self.out_temp = weather_temp

            if self.ADapi.datetime(aware=True) - self.rain_last_update > datetime.timedelta(minutes = 20):
                self.rain_amount = weather_rain_amount
            
            if self.ADapi.datetime(aware=True) - self.wind_last_update > datetime.timedelta(minutes = 20):  
                self.wind_amount = weather_wind_amount


            self.send_weather_update()


    def newOutTemp(self) -> None:
        """ Sets new out temp after comparing sensor 1 and 2 and time since the other was last updated.
        """
        if (
            self.ADapi.datetime(aware=True) - self.outTemp_last_update2 > datetime.timedelta(minutes = 20)
            or self.outTemp2 >= self.outTemp1
        ):
            self.out_temp = self.outTemp1
            self.send_weather_update()

        self.outTemp_last_update1 = self.ADapi.datetime(aware=True)


    def newOutTemp2(self) -> None:
        """ Sets new out temp after comparing sensor 1 and 2 and time since the other was last updated.
        """
        if (
            self.ADapi.datetime(aware=True) - self.outTemp_last_update1 > datetime.timedelta(minutes = 20)
            or self.outTemp1 >= self.outTemp2
        ):
            self.out_temp = self.outTemp2
            self.send_weather_update()

        self.outTemp_last_update2 = self.ADapi.datetime(aware=True)


    def rainSensorUpdated(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates rain amount from sensor
        """
        try:
            self.rain_amount = float(new)
        except ValueError as ve:
            self.ADapi.log(f"Not able to set new rain amount: {new}. {ve}", level = 'DEBUG')
        else:
            self.rain_last_update = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)

            self.send_weather_update()


    def anemometerUpdated(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates WIND_AMOUNT from sensor
        """
        try:
            self.wind_amount = float(new)
        except ValueError as ve:
            self.ADapi.log(f"Not able to set new wind amount: {new}. {ve}", level = 'DEBUG')
        else:
            self.wind_last_update = self.ADapi.datetime(aware=True) - datetime.timedelta(minutes = 20)

            self.send_weather_update()


        # Lux / weather
    def out_lux_state(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates lux data from sensors.
        """
        try:
            if self.outLux1 != float(new):
                self.outLux1 = float(new)
        except ValueError as ve:
            self.ADapi.log(f"Not able to get new outlux. ValueError: {ve}", level = 'DEBUG')
        except TypeError as te:
            self.ADapi.log(f"Not able to get new outlux. TypeError: {te}", level = 'DEBUG')
        except Exception as e:
            self.ADapi.log(f"Not able to get new outlux. Exception: {e}", level = 'WARNING')
        else:
            self.newOutLux()


    def out_lux_event_MQTT(self, event_name, data, kwargs) -> None:
        """ Updates lux data from MQTT event.
        """
        lux_data = json.loads(data['payload'])
        if 'illuminance_lux' in lux_data:
            if self.outLux1 != float(lux_data['illuminance_lux']):
                self.outLux1 = float(lux_data['illuminance_lux']) # Zigbee sensor
                self.newOutLux()
        elif 'illuminance' in lux_data:
            if self.outLux1 != float(lux_data['illuminance']):
                self.outLux1 = float(lux_data['illuminance']) # Zigbee sensor
                self.newOutLux()
        elif 'value' in lux_data:
            if self.outLux1 != float(lux_data['value']):
                self.outLux1 = float(lux_data['value']) # Zwave sensor
                self.newOutLux()


    def newOutLux(self) -> None:
        """ Sets new lux data after comparing sensor 1 and 2 and time since the other was last updated.
        """
        if (
            self.ADapi.datetime(aware=True) - self.lux_last_update2 > datetime.timedelta(minutes = 15)
            or self.outLux1 >= self.outLux2
        ):
            self.out_lux = self.outLux1
            self.send_weather_update()

        self.lux_last_update1 = self.ADapi.datetime(aware=True)


    def out_lux_state2(self, entity, attribute, old, new, kwargs) -> None:
        """ Updates lux data from sensors.
        """
        try:
            if self.outLux2 != float(new):
                self.outLux2 = float(new)
        except ValueError as ve:
            self.ADapi.log(f"Not able to get new outlux. ValueError: {ve}", level = 'DEBUG')
        except TypeError as te:
            self.ADapi.log(f"Not able to get new outlux. TypeError: {te}", level = 'DEBUG')
        except Exception as e:
            self.ADapi.log(f"Not able to get new outlux. Exception: {e}", level = 'WARNING')
        else:
            self.newOutLux2()


    def out_lux_event_MQTT2(self, event_name, data, kwargs) -> None:
        """ Updates lux data from MQTT event.
        """
        lux_data = json.loads(data['payload'])
        if 'illuminance_lux' in lux_data:
            if self.outLux2 != float(lux_data['illuminance_lux']):
                self.outLux2 = float(lux_data['illuminance_lux']) # Zigbee sensor
                self.newOutLux2()
        elif 'illuminance' in lux_data:
            if self.outLux2 != float(lux_data['illuminance']):
                self.outLux2 = float(lux_data['illuminance']) # Zigbee sensor
                self.newOutLux2()
        elif 'value' in lux_data:
            if self.outLux2 != float(lux_data['value']):
                self.outLux2 = float(lux_data['value']) # Zwave sensor
                self.newOutLux2()


    def newOutLux2(self) -> None:
        """ Sets new lux data after comparing sensor 1 and 2 and time since the other was last updated.
        """
        if (
            self.ADapi.datetime(aware=True) - self.lux_last_update1 > datetime.timedelta(minutes = 15)
            or self.outLux2 >= self.outLux1
        ):
            self.out_lux = self.outLux2
            self.send_weather_update()

        self.lux_last_update2 = self.ADapi.datetime(aware=True)


    def getOutTemp(self) -> float:
        """ Returns outdoor temperature
        """
        return self.out_temp