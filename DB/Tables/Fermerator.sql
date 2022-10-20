DROP TABLE IF EXISTS HopPi.Fermerator;

/*####################################

    Debug Block

    SELECT * FROM HopPI.Fermerator

####################################*/

CREATE TABLE HopPi.Fermerator(
   FermeratorId int PRIMARY KEY AUTO_INCREMENT
  ,TapNumber int
  ,BeerId int
  ,InitialVol decimal
  ,RemainingVol decimal
  ,DateOnTap datetime
);
