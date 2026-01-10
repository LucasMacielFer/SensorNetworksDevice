import json
import struct

class FormatterService:
    @staticmethod
    def format_for_mqtt(temperature, humidity, lux, altitude, pressure):
        dados = {
            "temperatura": temperature,
            "umidade": humidity,
            "pressao": pressure,
            "altura": altitude,
            "lux": lux,
            "source": 0,
            "active": 1
        }

        payload = json.dumps(dados)
        return payload
    
    @staticmethod
    def format_for_lorawan(temperature, humidity, lux, altitude, pressure):
        t_int = int(temperature * 100)
        h_int = int(humidity * 100)
        p_int = int(pressure/100)      # Pressão em hPa
        a_int = int(altitude)
        lux_int = int(lux)

        # Formato ">hhHhHH":
        # > : Big Endian (padrão de rede)
        # h : short (2 bytes com sinal, para temp e hum)
        # H : unsigned short (2 bytes sem sinal, para pressão e luz)
        # h : short (2 bytes com sinal, altitude pode ser negativa?)
        payload = struct.pack(">hhHhH", t_int, h_int, p_int, a_int, lux_int)
        return payload
    
    @staticmethod
    def get_lora_shutdown_payload():
        return b'\x00' * 10
    
    @staticmethod
    def get_mqtt_shutdown_payload():
        dados = {
            "source": 0,
            "active": 0
        }

        payload = json.dumps(dados)
        return payload