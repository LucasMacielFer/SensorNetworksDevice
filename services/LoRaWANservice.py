import network as nw
from network import LoRa
import time
import binascii
import socket

class LoRaWANService:
    def __init__(self, dev_eui, app_eui, app_key):
        self.dev_eui = binascii.unhexlify(dev_eui)
        self.app_eui = binascii.unhexlify(app_eui)
        self.app_key = binascii.unhexlify(app_key)

        self.lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)
        self.socket = None

        self.join_lorawan()

    def join_lorawan(self):
        print("[LoRaWAN] Iniciando o processo de junção LoRaWAN...")

        if not self.lora:
            self.lora = LoRa(mode=LoRa.LORAWAN, region=LoRa.EU868)

        self.lora.join(activation=LoRa.OTAA, auth=(self.dev_eui, self.app_eui, self.app_key), timeout=0)
        triesLeft = 12

        while not self.lora.has_joined() and triesLeft > 0:
            print("[LoRaWAN] Tentativas restantes para junção: {}".format(triesLeft))
            triesLeft -= 1
            time.sleep(5)

        if self.lora.has_joined():
            self.lora.nvram_save()
            self.socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
            if self.socket:
                self.socket.setblocking(False)
            print("[LoRaWAN] Junção LoRaWAN bem-sucedida!")
        else:
            print("[LoRaWAN] Falha na junção LoRaWAN após múltiplas tentativas.")

    def send_data(self, data):
        if not self.lora.has_joined():
            print("[LoRaWAN] Dispositivo não está conectado à rede LoRaWAN. Não é possível enviar dados.")
            return False
        
        if self.socket is None:
            try:
                self.socket = socket.socket(socket.AF_LORA, socket.SOCK_RAW)
            except:
                print("[LoRaWAN] Erro ao criar socket LoRaWAN.")
                print("[LoRaWAN] A desligar LoRa...")
                self.disconnect()
                return False

        try:
            self.socket.setsockopt(socket.SOL_LORA, socket.SO_DR, 3)
            self.socket.setblocking(True)
            self.socket.send(data)
            self.socket.setblocking(False)
            print("[LoRaWAN] Dados enviados via LoRaWAN: {}".format(data))
            return True
        except:
            print("[LoRaWAN] Erro ao enviar dados via LoRaWAN.")
            return False

    def get_socket(self):
        return self.socket
    
    def is_connected(self):
        if self.lora:
            return self.lora.has_joined()
        return False

    def is_socket_available(self):
        return self.socket is not None
    
    def disconnect(self):
        self.lora.nvram_save()

        if self.socket:
            self.socket.close()
            self.socket = None
        
        self.lora = None
        print("[LoRaWAN] Desconectado e estado salvo na NVRAM.")
