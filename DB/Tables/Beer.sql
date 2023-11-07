-- Postgres SQL

DROP TABLE IF EXISTS Beer;

/*####################################

    Debug Block

    SELECT * FROM Beer

####################################*/

CREATE TABLE Beer(
   BeerId SERIAL PRIMARY KEY
  ,Name varchar(50)
  ,SubStyleId int
  ,IBU int
)