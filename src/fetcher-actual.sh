#!/bin/bash
while :
do
	wget https://onlinedata.plzen.eu/data-pd-rychtarka-actual.php -O rychtarka-actual.csv
	wget https://onlinedata.plzen.eu/data-pd-novedivadlo-actual.php -O novedivadlo-actual.csv
	sleep 600 # sleep 10 minutes
done
