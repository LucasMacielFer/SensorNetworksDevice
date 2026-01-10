import network as nw
from lib.simple import MQTTClient
import time

class MQTTService:
    def __init__(self, ssid, password, user, broker, uuid):
        self.ssid = ssid
        self.password = password
        self.user = user
        self.broker = broker
        self.client = None
        self.wlan = None

        self.connect_to_wifi()
        if self.wlan.isconnected():
            self.client = self.connect_to_mqtt(uuid)

    def connect_to_wifi(self):
        wlan = nw.WLAN(mode=nw.WLAN.STA)
        triesLeft = 5

        try:
            if not wlan.isconnected():
                print('[WIFI] Conectando à rede...')
                print('[WIFI] Tentativas restantes: {}'.format(triesLeft))

                wlan.connect(self.ssid, auth=(nw.WLAN.WPA2, self.password))

                while not wlan.isconnected() and triesLeft > 0:
                    triesLeft -= 1
                    time.sleep(1)
            
            if wlan.isconnected():
                print('[WIFI] Conectado com sucesso!')
                print('[WIFI] Configuração de rede: {}'.format(wlan.ifconfig()))
            else:
                print('[WIFI] Falha ao conectar à rede.')

            self.wlan = wlan
        except:
            print('[WIFI] Erro ao conectar à rede WiFi.')
            self.wlan = None

    def connect_to_mqtt(self, uuid):
        try:
            self.client = MQTTClient(uuid, self.broker, user=self.user, password="", port=1883)
            self.client.connect()

            print("[MQTT] Conectado com sucesso ao Ubidots!")
            return self.client
        
        except:
            print("[MQTT] Falha ao conectar ao Ubidots")
            return None
        
    def publish(self, topic, message):
        if self.client:
            try:
                self.client.publish(topic, message)
                print("[MQTT] Mensagem publicada no tópico '{}': {}".format(topic, message))
                return True
            except:
                print("[MQTT] Falha ao publicar mensagem no tópico '{}'".format(topic))
                return False
        else:
            print("[MQTT] Cliente MQTT não está conectado. Não é possível publicar mensagens.")
            return False
        
    def is_connected(self):
        if self.wlan:
            return self.wlan.isconnected()
        return False
    
    def is_client_connected(self):
        return self.client is not None

    def get_wlan(self):
        return self.wlan

    def get_mqtt_client(self):
        return self.client
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()
            print("[MQTT] Desconectado do broker MQTT.")
        else:
            print("[MQTT] Cliente MQTT não está conectado.")

        if self.wlan:
            self.wlan.disconnect()
            print("[WIFI] Desconectado da rede WiFi.")

        self.client = None
        self.wlan = None
