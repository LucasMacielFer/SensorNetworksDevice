from services.SensorsService import SensorsService
from services.MQTTservice import MQTTService
from services.LoRaWANservice import LoRaWANService
from services.BLEservice import BLEService
from services.FormatterService import FormatterService

import pycom
import time
from network import Bluetooth

# Cores para o LED
COLOR_INACTIVE = 0x7F0000   # Vermelho
COLOR_MQTT = 0x00007F       # Azul
COLOR_LORAWAN = 0x7F007F    # Roxo
COLOR_INIT = 0x7F7F00       # Amarelo
COLOR_SENDING = 0x007F00    # Verde

# Configuração de temporização
TIME_BETWEEN_READINGS = 300

# Configurações WiFi e MQTT
WIFI_SSID = "***REMOVED***"
WIFI_PASSWORD = "***REMOVED***"
MQTT_USER = "***REMOVED***"
MQTT_BROKER = "industrial.api.ubidots.com"
MQTT_TOPIC = "***REMOVED***"
DEVICE_UUID = "***REMOVED***"

# Configurações LoRaWAN
LORAWAN_DEV_EUI = '***REMOVED***'
LORAWAN_APP_EUI = '***REMOVED***'
LORAWAN_APP_KEY = '***REMOVED***'

# Configurações BLE
BLE_DEVICE_NAME='LP***REMOVED***'
BLE_MANUFACTURER_DATA='PyCom'

def main():
    pycom.heartbeat(False)
    pycom.rgbled(COLOR_INIT)

    # Por padrão: Tenta primeiro MQTT
    cooldown_count = 0
    comm_mode = 1
    active = True
    set_inactive = False
    wifi_pwd = WIFI_PASSWORD
    wifi_ssid = WIFI_SSID
    wifi_changed = False
    woke_up = False

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
            nonlocal comm_mode, wifi_changed, active

            try:
                comm_mode = int(value[0])
            except:
                print('[BLE] MODE inválido')
                return

            if comm_mode == 1:
                print('[BLE] Modo MQTT selecionado.')
                wifi_changed = True
                if active:
                    pycom.rgbled(COLOR_INIT)
            elif comm_mode == 2:
                print('[BLE] Modo LoRaWAN selecionado.')
                if active:
                    pycom.rgbled(COLOR_INIT)
            else:
                print('[BLE] Modo desconhecido')

            ble_ack_queue.append(b'\x81\x01')  # ACK MODE

        # Active
        elif cmd == 0x02:
            nonlocal active, set_inactive, woke_up

            try:
                active = not (value[0] == 0)
            except:
                print('[BLE] ACTIVE inválido')
                return

            if active:
                set_inactive = False
                pycom.rgbled(COLOR_INIT)
                woke_up = True

            else:
                set_inactive = True
                pycom.rgbled(COLOR_INACTIVE)

            print('[BLE] Ativo:', active)
            ble_ack_queue.append(b'\x82\x01')  # ACK ACTIVE

        # SSID
        elif cmd == 0x03:
            nonlocal wifi_ssid, wifi_changed

            try:
                wifi_ssid = value.decode('utf-8')
                wifi_changed = True
                print('[BLE] SSID WiFi:', wifi_ssid)
                ble_ack_queue.append(b'\x83\x01')  # ACK SSID
            except:
                print('[BLE] SSID inválido')

        # Password
        elif cmd == 0x04:
            nonlocal wifi_pwd, wifi_changed

            try:
                wifi_pwd = value.decode('utf-8')
                wifi_changed = True
                print('[BLE] Senha WiFi recebida')
                ble_ack_queue.append(b'\x84\x01')  # ACK PWD
            except:
                print('[BLE] Password inválida')

        else:
            print('[BLE] CMD desconhecido:', cmd)


    # Inicializa serviços
    sensors_service = SensorsService()
    mqtt_service = MQTTService(WIFI_SSID, WIFI_PASSWORD, MQTT_USER, MQTT_BROKER, DEVICE_UUID)
    lorawan_service = LoRaWANService(LORAWAN_DEV_EUI, LORAWAN_APP_EUI, LORAWAN_APP_KEY)
    ble_service = BLEService(BLE_DEVICE_NAME, BLE_MANUFACTURER_DATA, conn_cb)
    ble_service.set_callback(ble_cmd_cb)

    while True:
        while ble_ack_queue:
            packet = ble_ack_queue.pop(0)  # retira o primeiro
            try:
                ble_service.send_notification(packet)
            except Exception as e:
                print('[BLE] Erro ao enviar ACK: ', e)

        if active:
            if wifi_changed:
                wifi_changed = False
                if (not mqtt_service.is_connected() or
                    mqtt_service.password != wifi_pwd or
                    mqtt_service.ssid != wifi_ssid):
                    
                    mqtt_service.password = wifi_pwd
                    mqtt_service.ssid = wifi_ssid
                    mqtt_service.connect_to_wifi()
                    mqtt_service.connect_to_mqtt(DEVICE_UUID)

            if woke_up:
                woke_up = False
                cooldown_count = 0
                print("[MAIN] Dispositivo acordado.")
                print("[MAIN] Tentando conectar...")

                if not mqtt_service.is_connected():
                    mqtt_service.connect_to_wifi()
                if not mqtt_service.is_client_connected():
                    mqtt_service.connect_to_mqtt(DEVICE_UUID)
                if not lorawan_service.is_connected():
                    lorawan_service.join_lorawan()

                if mqtt_service.is_client_connected() and mqtt_service.is_connected():
                    print("[MAIN] Reconectado ao MQTT Broker.")
                if lorawan_service.is_connected():
                    print("[MAIN] Reconectado à rede LoRaWAN.")
                

            if cooldown_count <= 0:
                cooldown_count = TIME_BETWEEN_READINGS
                # Lê dados dos sensores
                sensors_service.read_sensors()
                sensor_data = sensors_service.get_sensor_data()
                sensors_service.print_sensor_data()

                mqtt_available = mqtt_service.is_connected() and mqtt_service.is_client_connected()
                lorawan_available = lorawan_service.is_connected()

                use_mqtt = mqtt_available and comm_mode == 1 or (mqtt_available and not lorawan_available)
                use_lorawan = (lorawan_available and comm_mode == 2) or (not mqtt_available and lorawan_available)

                if use_mqtt:
                    mqtt_payload = FormatterService.format_for_mqtt(
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["lux"],
                        sensor_data["altitude"],
                        sensor_data["pressure"]
                    )

                    try:
                        pycom.rgbled(COLOR_SENDING)
                        mqtt_service.publish(MQTT_TOPIC, mqtt_payload)
                        time.sleep(0.1)
                        pycom.rgbled(COLOR_MQTT)
                    except:
                        print("[MAIN] Erro ao enviar dados via MQTT.")

                elif use_lorawan:
                    lorawan_payload = FormatterService.format_for_lorawan(
                        sensor_data["temperature"],
                        sensor_data["humidity"],
                        sensor_data["lux"],
                        sensor_data["altitude"],
                        sensor_data["pressure"]
                    )

                    try:
                        pycom.rgbled(COLOR_SENDING)
                        lorawan_service.send_data(lorawan_payload)
                        time.sleep(0.1)
                        pycom.rgbled(COLOR_LORAWAN)
                    except:
                        print("[MAIN] Erro ao enviar dados via LoRaWAN.")

                else:
                    cooldown_count = 0;
                    print("[MAIN] Nenhuma conexão disponível para envio de dados.")
                    print("[MAIN] Tentando reconectar...")
                    mqtt_service.connect_to_wifi()
                    mqtt_service.connect_to_mqtt(DEVICE_UUID)
                    lorawan_service.join_lorawan()

                    if mqtt_service.is_client_connected() and mqtt_service.is_connected():
                        print("[MAIN] Reconectado ao MQTT Broker.")
                    if lorawan_service.is_connected():
                        print("[MAIN] Reconectado à rede LoRaWAN.")

            time.sleep(5)
            cooldown_count -= 5

        else:
            if set_inactive:
                mqtt_available = mqtt_service.is_connected() and mqtt_service.is_client_connected()
                lorawan_available = lorawan_service.is_connected()
                use_mqtt = mqtt_available and comm_mode == 1 or (mqtt_available and not lorawan_available)
                use_lorawan = (lorawan_available and comm_mode == 2) or (not mqtt_available and lorawan_available)

                print("[MAIN] Dispositivo inativo. Enviando payloads de desligamento...")

                if use_mqtt:
                    mqtt_payload = FormatterService.get_mqtt_shutdown_payload()
                    mqtt_service.publish(MQTT_TOPIC, mqtt_payload)
                    time.sleep(1)

                elif use_lorawan:
                    lorawan_payload = FormatterService.get_lora_shutdown_payload()
                    lorawan_service.send_data(lorawan_payload)
                    time.sleep(1)

                set_inactive = False
                print("[MAIN] Payloads de desligamento enviados.")
                pycom.rgbled(COLOR_INACTIVE)

                mqtt_service.disconnect()
                lorawan_service.disconnect()
                print("[MAIN] Desconectado dos serviços de comunicação.")

            time.sleep(5)

if __name__ == "__main__":
    main()