from services.SensorsService import SensorsService
from services.MQTTservice import MQTTService
from services.LoRaWANservice import LoRaWANService
from services.BLEservice import BLEService
from services.FormatterService import FormatterService

import machine
import pycom
import time
from network import Bluetooth
from machine import Pin

# Cores para o LED
COLOR_INACTIVE = 0x7F0000   # Vermelho
COLOR_MQTT = 0x00007F       # Azul
COLOR_LORAWAN = 0x7F007F    # Roxo
COLOR_INIT = 0x7F7F00       # Amarelo
COLOR_SENDING = 0x007F00    # Verde

# Configuração de temporização
DEFAULT_TIME_BETWEEN_READINGS = 300

# Configurações WiFi e MQTT
WIFI_SSID = "***REDACTED***"
WIFI_PASSWORD = "***REDACTED***"
MQTT_USER = "***REDACTED***"
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_TOPIC = "***REDACTED***"
DEVICE_UUID = "***REDACTED***"

# Configurações LoRaWAN
LORAWAN_DEV_EUI = '***REDACTED***'
LORAWAN_APP_EUI = '***REDACTED***'
LORAWAN_APP_KEY = '***REDACTED***'

# Configurações BLE
BLE_DEVICE_NAME='LPLucas'
BLE_MANUFACTURER_DATA='PyCom'

# Constantes (modo de comunicação)
MODE_MQTT = 1
MODE_LORAWAN = 2
MAX_TRIES = 2

def main():
    pycom.heartbeat(False)
    pycom.rgbled(COLOR_INIT)

    active = True

    cooldown_count = 0
    comm_mode = MODE_MQTT
    wifi_pwd = WIFI_PASSWORD
    wifi_ssid = WIFI_SSID

    time_between_readings = DEFAULT_TIME_BETWEEN_READINGS

    ble_ack_queue = []

    # Callbacks BLE
    def conn_cb(bt_o):
        if bt_o.events() & Bluetooth.CLIENT_CONNECTED:
            print('[BLE] Client connected')
        if bt_o.events() & Bluetooth.CLIENT_DISCONNECTED:
            print('[BLE] Client disconnected')

    def ble_cmd_cb(chr, data):
        events, _ = data
        if not (events & Bluetooth.CHAR_WRITE_EVENT):
            return

        payload = chr.value()
        if len(payload) < 2:
            print('[BLE] Payload inválido')
            return

        cmd = payload[0]
        length = payload[1]
        value = payload[2:2 + length]

        if len(value) != length:
            print('[BLE] Tamanho do payload inconsistente: esperado {}, recebido {}'.format(length, len(value)))
            return

        nonlocal ble_ack_queue

        # Mode
        if cmd == 0x01:
            nonlocal comm_mode, active

            try:
                comm_mode = int(value[0])
            except:
                print('[BLE] MODE inválido')
                return

            if comm_mode == MODE_MQTT:
                print('[BLE] Modo MQTT selecionado.')
            else:
                comm_mode = MODE_LORAWAN
                print('[BLE] Modo LoRaWAN selecionado.')
                
            if active:
                pycom.rgbled(COLOR_INIT)

            ble_ack_queue.append(b'\x81\x01')  # ACK MODE

        # Active
        elif cmd == 0x02:
            nonlocal active

            active = False
            pycom.rgbled(COLOR_INACTIVE)

            print('[BLE] Dispositivo desativado.')
            ble_ack_queue.append(b'\x82\x01')  # ACK ACTIVE

        # SSID
        elif cmd == 0x03:
            nonlocal wifi_ssid

            try:
                wifi_ssid = value.decode('utf-8')
                print('[BLE] SSID WiFi:', wifi_ssid)
                ble_ack_queue.append(b'\x83\x01')  # ACK SSID
            except:
                print('[BLE] SSID inválido')

        # Password
        elif cmd == 0x04:
            nonlocal wifi_pwd

            try:
                wifi_pwd = value.decode('utf-8')
                print('[BLE] Senha WiFi recebida')
                ble_ack_queue.append(b'\x84\x01')  # ACK PWD
            except:
                print('[BLE] Password inválida')

        # Tempo
        elif cmd == 0x05:
            nonlocal time_between_readings

            try:
                time_between_readings = int(value[0])
                print('[BLE] Tempo entre leituras definido para {} segundos'.format(time_between_readings))
            except:
                print('[BLE] Tempo inválido')
                return

            ble_ack_queue.append(b'\x85\x01')  # ACK TIME

        else:
            print('[BLE] CMD desconhecido:', cmd)

    # Callback interrupção botão
    def int_btn(pin):
        nonlocal active
        active = False
        pycom.rgbled(COLOR_INACTIVE)
        print('[INT] Botão pressionado. Dispositivo desativado.')

    # Inicializa serviços
    sensors_service = SensorsService()
    lorawan_service = LoRaWANService(LORAWAN_DEV_EUI, LORAWAN_APP_EUI, LORAWAN_APP_KEY)
    ble_service = BLEService(BLE_DEVICE_NAME, BLE_MANUFACTURER_DATA, conn_cb)
    ble_service.set_callback(ble_cmd_cb)
    mqtt_service = None

    # Configura interrupção do botão
    btn = Pin('P14', mode=Pin.IN, pull=Pin.PULL_UP)
    btn.callback(trigger=Pin.IRQ_FALLING, handler=int_btn)

    while True:
        while ble_ack_queue:
            packet = ble_ack_queue.pop(0)  # retira o primeiro
            try:
                ble_service.send_notification(packet)
            except Exception as e:
                print('[BLE] Erro ao enviar ACK: ', e)

        if active:
            if cooldown_count <= 0:
                cooldown_count = time_between_readings

                # Lê dados dos sensores
                sensors_service.read_sensors()
                sensor_data = sensors_service.get_sensor_data()
                sensors_service.print_sensor_data()

                lorawan_available = lorawan_service.is_connected()

                # Se o utilizador tiver selecionadoo MQTT, ou se o LoRaWAN não estiver disponível
                if comm_mode == MODE_MQTT or not lorawan_available:
                    mqtt_service = MQTTService(wifi_ssid, wifi_pwd, MQTT_USER, MQTT_BROKER, DEVICE_UUID)
                    mqtt_available = mqtt_service.is_connected() and mqtt_service.is_client_connected()
                else:
                    mqtt_available = False

                if mqtt_available:
                    mqtt_payload = FormatterService.format_for_mqtt(
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["lux"],
                        sensor_data["altitude"],
                        sensor_data["pressure"]
                    )

                    try:
                        pycom.rgbled(COLOR_SENDING)
                        
                        for attempt in range(MAX_TRIES):
                            print("[MAIN] Tentativa {} de envio via MQTT...".format(attempt + 1))
                            success = mqtt_service.publish(MQTT_TOPIC, mqtt_payload)
                            time.sleep(1)

                            if success:
                                print("[MAIN] Dados enviados com sucesso via MQTT.")
                                break

                        if not success:
                            print("[MAIN] Falha ao enviar dados via MQTT após múltiplas tentativas.")

                        pycom.rgbled(COLOR_MQTT)
                        mqtt_service.disconnect()
                        print("[MAIN] Desconectado do WiFi.")
                    except:
                        print("[MAIN] Erro ao enviar dados via MQTT.")

                elif lorawan_available:
                    success = False
                    lorawan_payload = FormatterService.format_for_lorawan(
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["lux"],
                        sensor_data["altitude"],
                        sensor_data["pressure"]
                    )

                    try:
                        pycom.rgbled(COLOR_SENDING)

                        for attempt in range(MAX_TRIES):
                            print("[MAIN] Tentativa {} de envio via LoRaWAN...".format(attempt + 1))
                            success = lorawan_service.send_data(lorawan_payload)
                            time.sleep(1)

                            if success:
                                print("[MAIN] Dados enviados com sucesso via LoRaWAN.")
                                break

                        if not success:
                            print("[MAIN] Falha ao enviar dados via LoRaWAN após múltiplas tentativas.")

                        pycom.rgbled(COLOR_LORAWAN)
                    except:
                        print("[MAIN] Erro ao enviar dados via LoRaWAN.")

                else:
                    pycom.rgbled(COLOR_INACTIVE)
                    print("[MAIN] Nenhuma conexão disponível para envio de dados.")
                    print("[MAIN] Tentando reconectar...")
                    lorawan_service.join_lorawan()

                    if lorawan_service.is_connected():
                        print("[MAIN] Reconectado à rede LoRaWAN.")
                        pycom.rgbled(COLOR_INIT)
                        cooldown_count = 0;

            time.sleep(5)
            cooldown_count -= 5

        else:
            lorawan_available = lorawan_service.is_connected()
            if comm_mode == MODE_MQTT or not lorawan_available:
                mqtt_service = MQTTService(wifi_ssid, wifi_pwd, MQTT_USER, MQTT_BROKER, DEVICE_UUID)
                mqtt_available = mqtt_service.is_connected() and mqtt_service.is_client_connected()
            else:
                mqtt_available = False

            print("[MAIN] Dispositivo inativo. Enviando payload de desligamento...")

            if mqtt_available:
                mqtt_payload = FormatterService.get_mqtt_shutdown_payload()
                mqtt_service.publish(MQTT_TOPIC, mqtt_payload)
                mqtt_service.disconnect()
                time.sleep(1)
                print("[MAIN] Payload de desligamento enviado via MQTT.")

            elif lorawan_available:
                lorawan_payload = FormatterService.get_lora_shutdown_payload()
                lorawan_service.send_data(lorawan_payload)
                time.sleep(1)
                print("[MAIN] Payload de desligamento enviado via LoRaWAN.")

            else:
                print("[MAIN] Nenhuma conexão disponível para envio do payload de desligamento.")
    
            print("[MAIN] Entrando em modo de baixo consumo...")
            machine.pin_sleep_wakeup(['P14'], mode=machine.WAKEUP_ALL_LOW, enable_pull=True)
            machine.deepsleep()

if __name__ == "__main__":
    main()
