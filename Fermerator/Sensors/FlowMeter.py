import time,\
	random,\
	logging,\
	RPI.GPIO as GPIO,\
	logging,\
	requests,\
	Common.Enum.PourType as pt,\
	configparser as cp
### Begin. These probably need to be pulled.
# import beer_db
# import twitter_notify
# import slack_notify
# import ConfigParser
# import zope.event
### End

class FlowMeter():
	"""
	Code to read and pull data from a flow sensor
	"""

  # Constants
	PINTS_IN_A_LITER = 2.11338
	SECONDS_IN_A_MINUTE = 60
	MS_IN_A_SECOND = 1000.0
	MINIMUM_POUR_VOL_LBL = "minimum_pour_vol"

	####################
	#    Properties    #
	####################
	#region Properties
	@property
	def MinimumPourVol(self) -> float:
		return self._minimum_pour_vol

	@MinimumPourVol.setter
	def MinimumPourVol(self, val: float = 0.075) -> None:
		self._minimum_pour_vol = val
	
	# _minimum_pour_vol = 0.23 ## This is the minimum amount of volume to be poured before it is registered as a complete pour.
	
	@property
	def IsMetric(self) -> bool:
		if self._isMetric is None:
			self._isMetric = True
		return self._isMetric

	@IsMetric.setter
	def IsMetric(self,val: bool) -> None:
		self._isMetric = val

	# TODO: make this not dumb
	@property
	def Beverage(self) -> str:
		if self._beverage is None:
			self._beverage = 'beer'
		return self._beverage

	@Beverage.setter
	def Beverage(self,val: str) -> None:
		self._beverage = val

	@property
	def Enabled(self) -> bool:
		if self._enabled is None:
			self._enabled = True
		return self._enabled

	@Enabled.setter
	def Enabled(self,val: bool) -> None:
		self._enabled = val
	
	@property
	def Clicks(self) -> int:
		if self._clicks is None:
			self._clicks = 0
		return self._clicks

	@Clicks.setter
	def Clicks(self,val: int) -> None:
		self._clicks = val

	@property
	def LastClick(self) -> float:
		if self._lastClick is None:
			self._lastClick = 0.0
		return self._lastClick

	@LastClick.setter
	def LastClick(self,val: float) -> None:
		self._lastClick = val
	
	@property
	def Flow(self) -> float:
		if self._flow is None:
			self._flow = 0.0
		return self._flow

	@Flow.setter
	def Flow(self,val: float) -> None:
		self._flow = val
	
	@property
	def ThisPour(self) -> float:
		if self._thisPour is None:
			self._thisPour = 0.0
		if (self.IsMetric):
			return round(self.ThisPour, 3)
		else:
			return round(self.thisPour * self.PINTS_IN_A_LITER, 3)

	@ThisPour.setter
	def ThisPour(self,val: float) -> None:
		"""
		Sets the ThisPour variable
		:param val: volume in liters poured
		"""
		self._thisPour = val

	@property
	def TotalPour(self) -> float:
		if self._totalPour is None:
			self._totalPour = 0.0
		return self._totalPour

	@TotalPour.setter
	def TotalPour(self,val: float) -> None:
		"""
		Sets the TotalPour variable
		:param val: volume in liters poured
		"""
		self._totalPour = val

	@property
	def TapId(self) -> int:
		if self._tapId is None:
			self._tapId = 0
		return self._tapId

	@TapId.setter
	def TapId(self,val: int) -> None:
		self._tapId = val
	
	@property
	def Pin(self) -> int:
		if self._pin is None:
			self._pin = -1
		return self._pin

	@Pin.setter
	def Pin(self,val: int) -> None:
		self._pin = val

	@property
	def PreviousPour(self) -> float:
		if self._previous_pour is None:
			self._previous_pour = 0.0
		return self._previous_pour

	@PreviousPour.setter
	def PreviousPour(self,val: float) -> None:
		self._previous_pour = val

	# TODO: What are we doing here
	@property
	def Config(self) -> cp.ConfigParser:
		return self._config

	@Config.setter
	def Config(self,val: cp.ConfigParser) -> None:
		self._config = val
	
	@property
	def LastEventType(self) -> pt.PourType:
		if self._lastEventType is None:
			self._lastEventType = pt.PourType.RESET
		return self._lastEventType

	@LastEventType.setter
	def LastEventType(self,val: pt.PourType) -> None:
		self._lastEventType = val

	@property
	def Logger(self) -> logging.Logger:
		if self._logger is None:
			self._logger = logging.getLogger(__name__)
		return self._logger

	@Logger.setter
	def Logger(self,val: logging.Logger) -> None:
		self._logger = val

	@property
	def StandAloneMode(self) -> bool:
		if self._standAloneMode is None:
			self._standAloneMode = False
		return self._standAloneMode

	@StandAloneMode.setter
	def StandAloneMode(self, val: bool) -> None:
		self._standAloneMode = val

	#endregion

	#region Constructor
	def __init__(self,
		isMetric: bool,
		beverage: str,
		tap_id: int,
		pin: int,
		config: cp.ConfigParser,
		capacity: int = 5,
		standAloneMode: bool = False,
		minimum_pour_vol: float = 0.075
	) -> None:
		"""
		FlowMeter Constructor
		- bool isMetric: metric or not?
		- string beverage: name of the beverage passing through the line
		- int tap_id: how shall i identify myself?
		- int pin: the GPIO pin to listen on
		"""

		logger = logging.getLogger(__name__)
		GPIO.setmode(GPIO.BCM)  # use real GPIO numbering

		self.IsMetric = isMetric
		self.Beverage = beverage
		self.LastClick = int(time.time() * self.MS_IN_A_SECOND)
		self.TapId = tap_id
		self.Pin = pin
		self.Capacity = capacity
		self.Config = config # TODO: find a way to pull this out and make it decoupled from the config object
		self.StandAloneMode = standAloneMode
		self.MinimumPourVol = minimum_pour_vol

		GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	#endRegion

	#region Methods
	def Update(self, currentTime = int(time.time() * MS_IN_A_SECOND)) -> None:
		"""
		Sets a timestamp of the last pour event.
		- float currentTime: timestamp of a long
		"""
		self.Clicks += 1
		# get the time delta
		clickDelta = max((currentTime - self.LastClick), 1)
		# calculate the instantaneous speed
		if (self.Enabled and clickDelta < 1000):
			hertz = self.MS_IN_A_SECOND / clickDelta

			flow = hertz / (self.SECONDS_IN_A_MINUTE * 7.5)  # In Liters per second
			instPour = (flow * (clickDelta / self.MS_IN_A_SECOND))  # * 1.265 #1.265

			self.ThisPour += instPour
			self.TotalPour += instPour
		# Update the last click
		self.LastClick = currentTime

		# Log it
		# logger.info("event-bus: registered tap " + str(self.get_tap_id()) + " successfully")
		self.Logger.info("Tap[%i] Pour Event: %s pints." %( self.TapId, str(round(self.TotalPour,3))))

	#TODO: Potentially change this up
	def ResetPourStatus(self) -> None:
		"""
		This will reset a pour to a cleared event. this is needed to properly track what beer has already been registered in the database.
		"""
		self.LastEventType = pt.PourType.RESET

	# TODO: do we need this?
	def Clear(self) -> None:
		"""
		Clears an event.
		"""
		self.thisPour = 0
		self.totalPour = 0

	def ListenForPour(self):
		"""
		"""
		currentTime = int(time.time() * self.MS_IN_A_SECOND)
		
		#TODO: Look into this function when parts arrive
		if self.ThisPour > 0.0:
			pour_size = round(self.ThisPour * self.PINTS_IN_A_LITER, 3)
			pour_size2 = round(self.ThisPour * self.PINTS_IN_A_LITER,2)  # IDK what is going on here but it works and I am afraid to break it
			if pour_size != self.PreviousPour:
				logger.debug(
					"Tap: %s\t Poursize: %s vs %s" % (str(self.TapId), str(pour_size), str(self.PreviousPour)))
				if pour_size2 < 0.05:
					return # ignore small events
				self.PreviousPour = pour_size
				self.LastEventType = self.POUR_UPDATE # set last event status for event bus in boozer

			## Test if the pour is above the minimum threshold and if so, register and complete the pour action.
			if (self.ThisPour > self.MinimumPourVol and currentTime - self.LastClick > 10000):  # 10 seconds of inactivity causes a tweet
				self.Logger.info("--- REGISTERING-FULL-POUR   %s vs %s " % (str(self.ThisPour), str(self.MinimumPourVol)) ) 
				self.RegisterNewPour(currentTime)
				self.LastEventType = self.POUR_FULL # set last event status for event bus in boozer
			else:
				logger.debug("--- Pour -> %s vs Threshold -> %s " % (str(self.ThisPour), str(self.MinimumPourVol)) ) 

			#TODO: Potentially remove this since I don't think we really need an event bus and I don't know what zope is
			zope.event.notify(self) # notify the boozer event bus that a new pour has been registered. 
								# it will check 'last_event_type' to decide to kick off actions related to a full pour up just update the database for a half/min pour.

	def RegisterNewPour(self, currentTime):
		"""
		"""
		# reset the counter
		self.ThisPour = 0.0

		# display the pour in real time for debugging
		if self.ThisPour > 0.05: self.Logger.debug("[POUR EVENT] " + str(self.TapId) + ":" + str(self.ThisPour))

		# reset flow meter after each pour (2 secs of inactivity)
		if (self.ThisPour <= self.MinimumPourVol and currentTime - self.LastClick > 2000): self.ThisPour = 0.0

	#endRegion

def Main():
	# bring in config
	CONFIG_FILE = "./config.ini"
	config = ConfigParser.ConfigParser()
	config.read(CONFIG_FILE)
	# setup logging
	# do it
	testTapId = 4
	testTapGpioPin = 13
	test_tap = FlowMeter("not metric", "FlowmeterTestBeer", tap_id=testTapId, pin=testTapGpioPin, config=config, STANDALONE_MODE=True)

	logger = logging.getLogger()
	handler = logging.StreamHandler()
	formatter = logging.Formatter(
		'%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
	handler.setFormatter(formatter)
	logger.addHandler(handler)
	logger.setLevel(logging.DEBUG)
	logger.setLevel(logging.INFO)

	# setup the flowmeter event bus
	GPIO.add_event_detect(test_tap.Pin, GPIO.RISING, callback=lambda *a: test_tap.Update(), bouncetime=20)
	logger.info("flowmeter.py listening for pours")
	while True:
		test_tap.ListenForPour()
		time.sleep(0.01)

# it's go time.
if __name__ == "__main__":
	Main()