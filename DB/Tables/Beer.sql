DROP TABLE IF EXISTS HopPi.Beer;

/*####################################

    Debug Block

    SELECT * FROM HopPI.Beer

####################################*/

CREATE TABLE HopPi.Beer(
   BeerId int PRIMARY KEY AUTO_INCREMENT
  ,Name varchar(50)
  ,SubStyleId int
  ,IBU int
)