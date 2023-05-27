#!/bin/bash
while :
do
	wget https://onlinedata.plzen.eu/data-pd-rychtarka.php -O rychtarka-full.csv
	wget https://onlinedata.plzen.eu/data-pd-novedivadlo.php -O novedivadlo-full.csv
	sleep 3600 # sleep 1 hour
done
