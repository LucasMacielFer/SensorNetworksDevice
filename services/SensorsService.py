from lib.SI7006A20 import SI7006A20
from lib.LTR329ALS01 import LTR329ALS01
from lib.MPL3115A2 import MPL3115A2,ALTITUDE,PRESSURE
from lib.pycoproc_1 import Pycoproc

class SensorsService:
    def __init__(self):
        self.py = Pycoproc(Pycoproc.PYSENSE)
        self.si = SI7006A20(self.py)
        self.ltr = LTR329ALS01(self.py)
        self.mpl_h = MPL3115A2(self.py, mode=ALTITUDE)
        self.mpl_p = MPL3115A2(self.py, mode=PRESSURE)

        self.temperature = None
        self.humidity = None
        self.lux = None
        self.altitude = None
        self.pressure = None

    def read_sensors(self):
        self.altitude = self.__read_altitude()
        self.temperature = self.__read_temperature()
        self.humidity = self.__read_humidity()
        self.lux = self.__read_lux()
        self.pressure = self.__read_pressure()

    def get_sensor_data(self):
        return {
            "temperature": self.temperature,
            "humidity": self.humidity,
            "lux": self.lux,
            "altitude": self.altitude,
            "pressure": self.pressure
        }
    
    def print_sensor_data(self):
        print("\n[SENSORS] Dados dos sensores:")
        print("[SENSORS] Temperatura: {} °C".format(self.temperature))
        print("[SENSORS] Umidade: {} %".format(self.humidity))
        print("[SENSORS] Luz: {} lux".format(self.lux))
        print("[SENSORS] Altitude: {} m".format(self.altitude))
        print("[SENSORS] Pressão: {} Pa\n".format(self.pressure))
        
    def __read_temperature(self):
        temperature = self.si.temperature()
        return temperature
    
    def __read_humidity(self):
        humidity = self.si.humidity()
        return humidity

    def __read_lux(self):
        ch0, ch1 = self.ltr.light()
        lux = self.__calculate_lux(ch0, ch1)
        return lux

    def __read_altitude(self):
        altitude = self.mpl_h.altitude()
        return altitude
    
    def __read_pressure(self):
        pressure = self.mpl_p.pressure()
        return pressure

    def __calculate_lux(self, ch0, ch1):
        ALS_GAIN = 1.0  
        ALS_INT = 1.0 
        
        if (ch0 + ch1) == 0:
            return 0.0
            
        ratio = ch1 / (ch0 + ch1)
        
        if ratio < 0.45:
            lux = (1.7743 * ch0 + 1.1059 * ch1)
        elif ratio < 0.64:
            lux = (4.2785 * ch0 - 1.9548 * ch1)
        elif ratio < 0.85:
            lux = (0.5926 * ch0 + 0.1185 * ch1)
        else:
            lux = 0.0
            
        return lux / (ALS_GAIN * ALS_INT)