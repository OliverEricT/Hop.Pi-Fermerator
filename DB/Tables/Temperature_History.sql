DROP TABLE IF EXISTS Temperature_History

/*####################################

    Debug Block

    SELECT * FROM Temperature_History

####################################*/

CREATE TABLE Temperature_History (
	 RecordTime TIMESTAMP NOT NULL
	,TempSensorId INTEGER NOT NULL
	,Temperature REAL
)