from enum import Enum
class PourType(Enum):
	"""
	Type of the Pour Event
	"""
	RESET = 1
	FULL = 3
	UPDATE = 5