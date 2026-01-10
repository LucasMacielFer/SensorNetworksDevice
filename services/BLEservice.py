from network import Bluetooth
import ubinascii

class BLEService:
    UUID_SERVICE = ubinascii.unhexlify('FFFFFFFFFFFFFFFFFFFFFFFFFFFF0000')
    UUID_CHR_CMD = ubinascii.unhexlify('FFFFFFFFFFFFFFFFFFFFFFFFFFFF0001')

    def __init__(self, name, manufacturer_data, conn_cb):
        self.ble = Bluetooth()
        self.ble.callback(trigger=Bluetooth.CLIENT_CONNECTED | Bluetooth.CLIENT_DISCONNECTED, handler=conn_cb)

        self.ble.set_advertisement(name=name, manufacturer_data=manufacturer_data)
        self.service = self.ble.service(uuid=self.UUID_SERVICE, isprimary=True)
        self.chr_cmd = self.service.characteristic(uuid=self.UUID_CHR_CMD, properties=Bluetooth.PROP_WRITE | Bluetooth.PROP_NOTIFY, value=b'\x01')

        self.ble.advertise(True)

    def set_callback(self, callback):
        self.chr_cmd.callback(trigger=Bluetooth.CHAR_WRITE_EVENT, handler=callback)

    def send_notification(self, data):
        self.chr_cmd.value(data)
