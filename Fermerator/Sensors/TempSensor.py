import time
import json
import requests
import logging
import sys
import os
import glob
import Common.Enum.SensorType as st

class TempSensor():
	"""
	Class to read the temperature from either a probe or an api endpoint
	"""

	DEGREES = "°"
	BASE_DIR = "/sys/bus/w1/devices/"

	#region Properties
	@property
	def SensorProtocol(self) -> st.SensorType:
		"""
		Denotes the sensor type that the instance is using
		"""
		return self._sensorProtocol

	@SensorProtocol.setter
	def SensorProtocol(self, val: st.SensorType) -> None:
		self._sensorProtocol = val

	@property
	def SensorId(self) -> str:
		return self._sensorId

	@SensorId.setter
	def SensorId(self, val: str) -> None:
		self._sensorId = val

	@property
	def SensorUrl(self) -> str:
		return self._sensorUrl

	@SensorUrl.setter
	def SensorUrl(self, val: str) -> None:
		self._sensorUrl = val

	@property
	def IsMetric(self) -> bool:
		return self._IsMetric

	@IsMetric.setter
	def IsMetric(self, val: bool) -> None:
		self._IsMetric = val

	@property
	def Logger(self) -> logging.Logger:
		return self._logger

	@Logger.setter
	def Logger(self, val: logging.Logger) -> None:
		self._logger = val

	@property
	def Temperature(self) -> float:
		if self.SensorProtocol == st.SensorType.HTTP:
			return self._GetTemperatureByHttp()
		else:
			return self.ReadDS18B20Sensor(self.SensorId)

	@property
	def Fahrenheit(self) -> float:
		if self.IsMetric:
			return self.ToFahrenheit(self.Temperature)
		else:
			return self.Temperature

	@property
	def Celsius(self) -> float:
		if self.IsMetric:
			return self.Temperature
		else:
			return self.ToCelsius(self.Temperature)

	#endRegion

	#region Constructor
	def __init__(self,
		sensor_protocol: st.SensorType = st.SensorType.NONE,
		sensor_id: str = "",
		sensor_url: str = "",
		isMetric: bool = True
	) -> None:
		"""
		TempSensor Constructor
		- SensorType sensor_protocol: 
		- str sensor_id: 
		- str sensor_url: 
		- bool isMetric: if true then return Celsius, else Fahrenheit
		"""
		self.Logger = logging.getLogger(__name__)
		self.Logger.info("TempSensor initializing")

		self.SensorProtocol = sensor_protocol
		if self.SensorProtocol == st.SensorType.DS18B20:
			os.system('modprobe w1-gpio')
			os.system('modprobe w1-therm')
			if sensor_id == "": 
				self.SensorId = self.GetDS18B20SensorIds()[0] # if user does not specify, just pick the first one.
			else:
				self.SensorId = sensor_id
		elif self.SensorProtocol != st.SensorType.HTTP:
			self.Logger.error("Configuration error. temperature sensor_protocol must map to DS18B20 or HTTP")
			sys.exit(1)

		self.SensorUrl = sensor_url
		self.IsMetric = isMetric
	
	#endRegion

	#region Methods
	def _GetTemperatureByHttp(self) -> float:
		try:
			r = requests.get(self.SensorUrl)
			if r.status_code == 200:
				if self.IsMetric:
					return r.text
				else:
					return self.ToFahrenheit(int(r.text))
			else:
				self.Logger.error("error: temperature sensor received http_code %i" % r.status_code)
		except:
			self.Logger.error("Temperature. Unable to get temperature from sensor_url: %s" % self.SensorUrl)

		return 0.0

	def ToFahrenheit(self, temperature: float) -> float:
		return (temperature * 9.0 / 5.0 + 32.0)

	def ToCelsius(self, temp: float) -> float:
		return ((temp - 32) / 1.80000)

	def ReadDS18B20Sensor(self, sensor_id: str) -> float:
		lines = self.ReadTempRaw(sensor_id)
		return self.ProcessRawDS18B20Data(lines, sensor_id)

	def GetDS18B20SensorIds(self) -> list[str]:
		numSensors = len(glob.glob(self.BASE_DIR + '28*'))
		sensor_ids=[]
		for x in range(0,numSensors):
			device_folder = glob.glob(self.BASE_DIR + '28*')[x]
			id = device_folder.replace(self.BASE_DIR,'')
			sensor_ids.append(id)
			self.Logger.info("discovered sensor id %s " % str(id))
		return sensor_ids

	def ProcessRawDS18B20Data(self, lines: list[str], sensor_id: str) -> float:
		while lines[0].strip()[-3:] != 'YES': # TODO: wtf is this shit
			time.sleep(0.2)
			lines = self.ReadTempRaw(sensor_id)

		equals_pos = lines[1].find('t=')
		if equals_pos != -1:
			temp_string = lines[1][equals_pos+2:]
			temp_c = float(temp_string) / 1000.0
			if self.IsMetric:
				return temp_c
			else:
				return self.ToFahrenheit(temp_c)

		return 0.0

	def ReadTempRaw(self, sensor_id: str) -> list[str]:
		device_folder = glob.glob(self.BASE_DIR + sensor_id)[0]
		device_file = device_folder + '/w1_slave'
		f = open(device_file, 'r')
		lines = f.readlines()
		f.close()
		return lines

def Main() -> None:
	t = TempSensor(sensor_protocol=st.SensorType.DS18B20)
	print("Read in: %s " % str(t.Temperature))

#endRegion

if __name__ == "__main__":
	Main()