from enum import Enum
class SensorType(Enum):
	"""
	Type of temperature sensor
	"""
	NONE = 0
	DS18B20 = 1
	HTTP = 2