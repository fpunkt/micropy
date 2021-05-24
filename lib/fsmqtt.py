"""
MQTT
"""

# pylint: disable=import-error, missing-docstring, redefined-builtin, too-many-arguments, no-member

import secrets
import board
import umqttsimple

class MQTTClient:
    def __init__(self):
        #self.client_id = client_id
        self.client = umqttsimple.MQTTClient(board.LOCATION, secrets.mqtt_server)

    def connect(self):
        self.client.connect()
        return self

    def publish(self, topic, payload):
        if self.client.sock is None:
            return
        self.client.publish(topic, payload)

    def publish_sensor_state(self, sensortype, sensorid, payload):
        if self.client.sock is None:
            return
        topic = 'ha/sensor/{}_{:02d}/state'.format(board.LOCATION, sensorid)
        self.client.publish(topic, payload)

    def publish_sensor_status(self, sensortype, sensorid, payload):
        if self.client.sock is None:
            return
        topic = 'ha/sensor/{}_{:02d}/status'.format(board.LOCATION, sensorid)
        self.client.publish(topic, payload)
