import RPi.GPIO as GPIO
import logging
import time

class Relay:
	"""
	Class to handle the relay for toggling the cooler/heater.
	"""

	LOGGING_FORMAT = "%(asctime)s [RELAY] %(message)s"

	@property
	def Pin(self) -> int:
		"""Pin the relay is using"""
		return self._Pin
	
	@Pin.setter
	def Pin(self,val: int) -> None:
		self._Pin = val

	@property
	def State(self) -> bool:
		return self._State
	
	@State.setter
	def State(self,val: bool) -> None:
		"""Is the Relay on or Off"""
		self._State = val

	@property
	def IsNO(self) -> bool:
		"""Is the Circuit normally open or closed"""
		return self._IsNO
	
	@IsNO.setter
	def IsNO(self,val: bool) -> None:
		self._IsNO = val

	def __init__(self, pin: int = 0, isNO: bool = False) -> None:
		self.Pin = pin
		self.IsNO = isNO
		self.State = True if self.IsNO else False

		GPIO.cleanup()

		logging.basicConfig(format=self.LOGGING_FORMAT)
		self.Logger = logging.getLogger(__name__)
		self.Logger.info("Relay initializing")
		self.Logger.debug(f"Pin: {self.Pin}")
		self.Logger.debug(f"Is Normally Open: {self.IsNO}")
		self.Logger.debug(f"Current State: {self.State}")

		GPIO.setmode(GPIO.BCM)
		GPIO.setup(self.Pin, GPIO.OUT)

	def Toggle(self) -> None:
		self.State = not self.State
		self.Logger.info("Toggling State")
		self.Logger.debug(f"Current State: {self.State}")
		

	def Output(self) -> None:
		"""Sends the current state to the GPIO"""
		GPIO.output(self.Pin, self.State)
		self.Logger.info("Sending the current state to the relay")
		self.Logger.debug(f"Current State: {self.State}")

def Main():
	relay = Relay(21)
	while True:
		relay.Output()
		relay.Toggle()
		print('Toggle 1')
		time.sleep(2)
		relay.Output()
		relay.Toggle()
		time.sleep(2)
		print('Toggle 2')

if __name__ == "__main__":
	Main()
