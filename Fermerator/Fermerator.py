import os,\
	time,\
	math,\
	logging,\
	requests,\
	Sensors.TempSensor,\
	Sensors.FlowMeter,\
	sys,\
	socket,\
	configparser as cp,\
	Common.Enum.SensorType as st
from xml.sax.handler import property_declaration_handler
from FlowMeter import FlowMeter
from TempSensor import TempSensor
from contextlib import closing
from typing import List

import pyfiglet
# import RPi.GPIO as GPIO
import beer_db
import ConfigParser
import bar_mqtt
import zope.event
from prettytable import PrettyTable
import influxdb_client

class Fermerator:

	#region Properties

	@property
	def Config(self) -> cp.ConfigParser:
		return self._config

	@Config.setter
	def Config(self, val: cp.ConfigParser) -> None:
		self._config = val

	@property
	def Logger(self) -> logging.Logger:
		return self._logger

	@Logger.setter
	def Logger(self, val: logging.Logger) -> None:
		self._logger = val

	#TODO: Potentially delete this
	@property
	def Database(self) -> str:
		return self._database

	@Database.setter
	def Database(self, val: str) -> None:
		self._database = val

	#TODO: Potentially delete this
	@property
	def MQTTEnabled(self) -> bool:
		return self._mqttEnabled

	@MQTTEnabled.setter
	def MQTTEnabled(self, val: bool) -> None:
		self._mqttEnabled = val

	#TODO: Potentially delete this
	@property
	def InfluxEnabled(self) -> bool:
		return self._influxEnabled
	
	@InfluxEnabled.setter
	def InfluxEnabled(self,val: bool) -> None:
		self._influxEnabled = val

	#TODO: Potentially delete this
	@property
	def TwitterEnabled(self) -> bool:
		return self._TwitterEnabled
	
	@TwitterEnabled.setter
	def TwitterEnabled(self,val: bool) -> None:
		self._TwitterEnabled = val

	#TODO: potentially delete this
	@property
	def ScrollphatEnabled(self) -> bool:
		return self._ScrollphatEnabled
	
	@ScrollphatEnabled.setter
	def ScrollphatEnabled(self,val: bool) -> None:
		self._ScrollphatEnabled = val

	@property
	def TemperatureEnabled(self) -> bool:
		return self._TemperatureEnabled
	
	@TemperatureEnabled.setter
	def TemperatureEnabled(self,val: bool) -> None:
		self._TemperatureEnabled = val

	@property
	def Taps(self) -> List[FlowMeter]:
		return self._Taps
	
	@Taps.setter
	def Taps(self,val: List[FlowMeter]) -> None:
		self._Taps = val

	@property
	def TemperatureClient(self) -> TempSensor:
		return self._TemperatureClient
	
	@TemperatureClient.setter
	def TemperatureClient(self,val: TempSensor) -> None:
		self._TemperatureClient = val

	#endRegion
	
	CONFIG_FILEPATH = os.getenv("CONFIG_FILEPATH", "./config.ini")
	DB_FILEPATH = os.getenv("DB_FILEPATTH","./db.sqlite")
	scrollphat_cleared = True ## TODO: decouple this
	
	mqtt_client = None
	twitter_client = None
	boozer_display = None
	slack_client = None
	temperature_client = None
	
	INFLUXDB_LBL = "Influxdb"

	def __init__(self) -> None:
		if not os.path.isfile(self.DB_FILEPATH):
			self.Logger.fatal("[fatal] cannot load db from " % self.DB_FILEPATH)
			sys.exit(1)
		if not os.path.isfile(self.CONFIG_FILEPATH):
			self.Logger.fatal("[fatal] cannot load config from " % self.CONFIG_FILEPATH)
			sys.exit(1)
		
		# Setup the configuration
		self.Config = cp.ConfigParser()
		self.Config.read(self.CONFIG_FILEPATH)

		# Set the self.Logger
		self.InitLogger()
		
		#TODO: Use different database client
		self.Database = beer_db.BeerDB(self.DB_FILEPATH)  # TODO: replace this with configuration value
		
		# setup temperature client
		self.InitTemperature()

		# setup scrollphat client
		try:
			if self.config.getboolean("Scrollphat", "enabled"):
				import boozer_display
				self.SCROLLPHAT_ENABLED = True
				self.boozer_display = boozer_display.BoozerDisplay()
		except: 
			self.Logger.info("Scrollphat Entry not found in %s, setting SCROLLPHAT_ENABLED to False")
			self.SCROLLPHAT_ENABLED = False

		# set up the flow meters
		#  _
		#| |_ __ _ _ __  ___
		#| __/ _ | '_ \/ __|
		#| || (_| | |_) \__ \
		# \__\__,_| .__/|___/
		#		 |_|

		for tap in range(1,10): # limit of 10 taps
			str_tap = "tap%i" % tap 
			str_tapN_gpio_pin = "%s_gpio_pin" % str_tap
			str_tapN_beer_name = "%s_beer_name" % str_tap
			str_tapN_reset_database = "%s_reset_database" % str_tap
			capacity_gallons = 5 # default is 5 gallons

			# see if the user set the capacity
			try:
				capacity_gallons = self.config.getint("Taps", str_tapN_gallon_capacity)
				self.Logger.info("Tap %i Config Override: Setting capacity to %i" % (tap, capacity_gallons))
			except:
				self.Logger.info("Tap %i: Setting capacity to %i" % (tap, capacity_gallons))

			try:
				this_tap_gpio_pin = self.config.getint("Taps", str_tapN_gpio_pin) # this looks for the tap gpio pin such as "tap1_gpio_pin"
				this_tap_beer_name = self.config.get("Taps", str_tapN_beer_name)
				new_tap = FlowMeter("not metric", this_tap_beer_name, tap_id=tap, pin=this_tap_gpio_pin, config=self.config, capacity=capacity_gallons, minimum_pour_vol=minimum_pour_vol) # Create the tap object
				self.taps.append(new_tap) # Add the new tap object to the array
			except:
				break

			# If mqtt is enabled, we need to push the new value. This is because mqtt does not always persist and that's a good thing to do.
			if self.MQTT_ENABLED:
				self.update_mqtt(tap, beverage_name=new_tap.get_beverage_name())

			# Check to see if we need to reset the database value
			try:
				if self.config.getboolean('Taps', str_tapN_reset_database):
					self.db.reset_tap_val(tap)
					self.Logger.info("Detected %s. Successfully reset the database entry to 100 percent volume remaining." % str_tapN_reset_database)
			except:
				continue

		if len(self.taps) < 1:
			# if there were no taps read in, there's no point living anymore. go fatal
			self.Logger.fatal("FATAL - No taps were read in from the config file. Are they formatted correctly?")
			sys.exit(1)
		## TODO This needs to be pulled into the init script 
		for tap in self.taps:  # setup all the taps. add event triggers to the opening of the taps.
			GPIO.add_event_detect(tap.get_pin(), GPIO.RISING, callback=lambda *a: self.register_tap(tap), bouncetime=20)
			#if MQTT_ENABLED: update_mqtt(tap.get_tap_id()) # do a prelim mqtt update in case it's been awhile

		zope.event.subscribers.append(self.register_pour_event) # Attach the event

	#########################
	#	Init helpers		#
	#########################

	def InitLogger(self):
		self.Logger = logging.getLogger()
		handler = logging.StreamHandler()
		formatter = logging.Formatter(
			'%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
		handler.setFormatter(formatter)
		self.Logger.addHandler(handler)
		self.Logger.setLevel(logging.INFO)
		# Check to see if we need to override the logging level
		try:
			level = self.Config.get("Boozer", "logging_level")
			level = level.upper()
			if level == "INFO":
				self.Logger.setLevel(logging.INFO)
			if level == "WARN":
				self.Logger.setLevel(logging.WARN)
			if level == "DEBUG":
				self.Logger.setLevel(logging.DEBUG)
			if level == "ERROR":
				self.Logger.setLevel(logging.ERROR)
		except Exception, e:
			self.Logger.debug("not overriding the logging level. error: " + str(e))

	def InitTemperature(self) -> None:
		self.TemperatureEnabled = self.Config.getboolean("Temperature", "enabled")
		self.Logger.info(f"TEMPERATURE_ENABLED = {self.TemperatureEnabled}")

		sensorUrl = self.Config.get("Temperature", "endpoint") or ""
		sensorProtocol = st.SensorType(self.Config.get("Temperature", "sensor_protocol")) or st.SensorType.NONE

		self.TemperatureClient = TempSensor(
																		sensor_protocol=sensorProtocol,
																		sensor_url=sensorUrl
																		)

	def update_mqtt(self, tap_id="-1", beverage_name="default_beverage"):
		"""
		:param tap_id:
		:return:
		"""
		percent = self.db.get_percentage100(tap_id)
		volume_topic = "bar/tap%s/value" % str(tap_id)
		beverage_name_topic="bar/tap%s/beverage" % str(tap_id)
		try:
			#Update the volume
			self.mqtt_client.pub_mqtt(volume_topic, str(percent))
			#Update the beverage name
			self.mqtt_client.pub_mqtt(beverage_name_topic, str(beverage_name))
		except:
			self.Logger.error("Unable to publish mqtt update for tap: %i " % int(tap_id)	)
			self.Logger.error(sys.exc_info()[0])

	# More config
	def is_port_open(self, host, port):
		import socket
		status = True
		
		with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
			sock.settimeout(2) 
			if sock.connect_ex(((host), (port))) == 0:
				status = False
		return status

	def get_enabled_string(self, val):
		if val == True:
			return "enabled"
		else:
			return "disabled"

	def print_config(self):
		result = pyfiglet.figlet_format("BOOZER") #, font = "slant" ) 
		print
		print
		print result

		files_table = PrettyTable(['File','Filepath', 'Exists'])
		files_table.add_row(['Database', self.DB_FILEPATH, os.path.isfile(self.DB_FILEPATH)])
		files_table.add_row(['Configuration', self.CONFIG_FILEPATH, os.path.isfile(self.CONFIG_FILEPATH)])
		print files_table

		t = PrettyTable(['Feature','Status'])
		t.add_row(['Twitter', self.get_enabled_string(self.TWITTER_ENABLED)])
		t.add_row(['Mqtt', self.get_enabled_string(self.MQTT_ENABLED)])
		t.add_row(['Temperature', self.get_enabled_string(self.TEMPERATURE_ENABLED)])
		t.add_row(['Slack', self.get_enabled_string(self.SLACK_ENABLED)])
		t.add_row(['Scrollphat', self.get_enabled_string(self.SCROLLPHAT_ENABLED)])
		print t

		taps_table = PrettyTable(['Tap','Beer','Capacity (Gallons)','GPIO Pin', 'Volume Remaining'])
		for tap in self.taps:
			taps_table.add_row([str(tap.get_tap_id()), str(tap.get_beverage_name()[0]), str(tap.capacity), str(tap.get_pin()), str(self.db.get_percentage100(tap.get_tap_id()))])
		print taps_table

		if self.INFLUXDB_ENABLED:
			influx_table = PrettyTable(['Key','Value'])
			influx_table.add_row(['influxdb','enabled'])
			influx_table.add_row(['database', str(self.influxdb_client.database)])
			influx_table.add_row(['host', str(self.influxdb_client.host)])
			influx_table.add_row(['port', str(self.influxdb_client.port)])
			influx_table.add_row(['username', str(self.influxdb_client.username)])
			influx_table.add_row(['password', str(self.influxdb_client.password)])
			print influx_table

		if self.MQTT_ENABLED == True:
			mqtt_host = self.config.get("Mqtt", "broker")
			mqtt_port = self.config.get("Mqtt", "port")
			mqtt_table = PrettyTable(['MQTT-Key','MQTT-Value'])
			mqtt_table.add_row(['broker', str(mqtt_host)])
			mqtt_table.add_row(['port', str(mqtt_port)])
			try:
				mqtt_table.add_row(['username', self.config.get("Mqtt", "username")])
				mqtt_table.add_row(['password', self.config.get("Mqtt", "password")])
			except:
				self.Logger.debug("skipping mqtt table generation for username and password because at least one was missing.")
			conn_str = "Connected"
			if self.is_port_open(host=mqtt_host, port=int(mqtt_port)):
				conn_str = "Unable to Connect"
			mqtt_table.add_row(['Connected?', conn_str])

			print mqtt_table

		if self.TEMPERATURE_ENABLED == True:
			temperature_table = PrettyTable(['Sensor','Temperature'])
			t = self.get_temperature_str()
			temperature_table.add_row(['temperature',self.get_temperature_str()])
			print temperature_table

	def get_temperature_str(self):
		return str(self.get_temperature()) + beer_temps.DEGREES		


	def get_temperature(self):
		"""
		Parses a http GET request for the connected temperature sensor. Yes, this
		relies on an external sensor-serving process, I recommend https://github.com/bgulla/sensor2json
		:return: string
		"""
		return self.temperature_client.get_temperature()


	def record_pour(self, tap_id, pour):
		self.db.update_tap(tap_id, pour)

	def register_tap(self, tap_obj):
		"""
		:param tap_obj:
		:return:
		"""
		currentTime = int(time.time() * FlowMeter.MS_IN_A_SECOND)
		tap_obj.update(currentTime)

	def register_pour_event(self, tap_obj ):
		tap_event_type = tap_obj.last_event_type

		if tap_event_type == FlowMeter.POUR_FULL:
			# we have detected that a full beer was poured
			self.register_new_pour(tap_obj)
		elif tap_event_type == FlowMeter.POUR_UPDATE:
			if self.SCROLLPHAT_ENABLED:
				try:

					current_pour = str(round(tap_obj.get_previous_pour(),2))
					# okay, i know this looks weird but since the scrollphat can only 
					# display a few chars, I hacked off the 0.
					first_digit = current_pour[0]
					if first_digit == 0:
						current_pour = current_pour[1:]
					self.boozer_display.set_display(current_pour)
				except:
					self.Logger.error("SCROLLPHAT: unable to update the display with the mid-pour volume amt")
			# it was just a mid pour 
			# TODO: Update scrollphat here
			self.Logger.debug("flowmeter.POUR_UPDATE")
			#print "brandon do something like update the scrollphat display or do nothing. it's cool"
	
	def get_pour_announcement(self,volume_poured, volume_remaining, beverage_name="default-beverage", tap_id="default-tapid" ):
		msg = "I just poured " 
		msg = msg + str(volume_poured) 
		msg = msg + " pints of " + str(beverage_name) 
		msg = msg +  " from tap " + str(tap_id) 
		msg = msg + " (" + str(volume_remaining) 
		msg = msg + "% remaining) "
		
		if self.TEMPERATURE_ENABLED:
			msg = msg + "at " + str(temperature) + beer_temps.DEGREES + "."
		else:
			msg = msg[:-1] + "."
		return msg


	def tweet_new_pour(self, msg):
		try:
			self.Logger.info("Twitter is enabled. Preparing to send tweet.")
			# calculate how much beer is left in the keg
			# tweet of the record
			self.twitter_client.post_tweet(msg)
			self.Logger.info("Tweet Sent: %s" % msg)
		except Exception, e:
			self.Logger.error("ERROR unable to send tweet: " + str(e) )
			self.Logger.error(sys.exc_info()[0])

	def update_database_with_new_pour(self, tap_id, total_pour_size, capacity_gallons):
		try:
			self.db.update_tap(tap_id, total_pour_size, capacity_gallons) # record the pour in the db
			self.Logger.info("Database updated: %s %s. " % (str(tap_id), str(total_pour_size)), )
		except Exception, e:
			self.Logger.error("unable to register new pour event to db: " + str(e))

	def register_new_pour(self, tap_obj):
		"""
		"""
		pour_size = round(tap_obj.thisPour * tap_obj.PINTS_IN_A_LITER, 3)
		total_pour_size = round(tap_obj.totalPour * tap_obj.PINTS_IN_A_LITER, 3)
		volume_remaining = (self.db.get_percentage100(tap_obj.tap_id))
		# record that pour into the database
		self.Logger.info("POUR this pour was %s pints (thisPour=%s vs totalPour=%s" % (str(pour_size), str(tap_obj.thisPour), str(tap_obj.totalPour)))
		
		self.update_database_with_new_pour(tap_obj.tap_id, total_pour_size, capacity_gallons=tap_obj.get_gallon_capacity())
		volume_remaining = (self.db.get_percentage100(tap_obj.tap_id))
		
		# calculate how much beer is left in the keg
		#volume_remaining = str(round(db.get_percentage(tap_obj.tap_id), 3) * 100)
		
		# Notification Agents
		if self.TWITTER_ENABLED or self.SLACK_ENABLED:
			try:
				pour_msg = self.get_pour_announcement(total_pour_size, str(volume_remaining), str(tap_obj.get_beverage_name()), str(tap_obj.get_tap_id()))
				if self.TWITTER_ENABLED: 
					self.tweet_new_pour(pour_msg)
				if self.SLACK_ENABLED:
					self.slack_client.post_slack_msg(pour_msg)
			except Exception, e:
				self.Logger.error("unable create notification.")
		
		# publish the updated value to mqtt broker
		if self.MQTT_ENABLED: 
			self.update_mqtt(tap_obj.get_tap_id(),beverage_name=tap_obj.get_beverage_name())
		
		# reset the counter
		self.Logger.info("Pour processing complete. Reseting pour of tap %i amount to 0.0" % tap_obj.get_tap_id())
		tap_obj.thisPour = 0.0
		tap_obj.totalPour = 0.0

		# reset the pour event flag
		tap_obj.last_event_type = FlowMeter.POUR_RESET

	def run(self):

		self.print_config()
		self.Logger.info("Boozer Intialized! Waiting for pours. Drink up, be merry!")
		counter = 0
		while True:

			# Handle keyboard events
			currentTime = int(time.time() * FlowMeter.MS_IN_A_SECOND)
			
			for tap in self.taps:
				tap.listen_for_pour()
			
			# push to influx if enabled
			counter = counter + 0.01
			if self.INFLUXDB_ENABLED:
				if counter > 60:
					if self.TEMPERATURE_ENABLED:
						self.influxdb_client.write_metric(self.temperature_client.get_temperature())
					counter = 0

			# go night night
			time.sleep(0.01)


def main():
	boozer = Boozer()
	boozer.run()


if __name__ == "__main__":
	main()