
class MQTTClient:
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def connect(self):
        print("MQTTClient.connect() called with", self.a, self.b)

    def publish(self, topic, message):
        print("MQTTClient.publish() called with", topic, message)
