#!/bin/bash

for i in $(seq 2005 1 2015); do
 
 cp /home/548/ab4502/working/ExtremeWind/jobs/barra_points/barra_points_generic.sh /home/548/ab4502/working/ExtremeWind/jobs/barra_points/barra_points_$i.sh

 sed -i "s/YEAR/$i/g" /home/548/ab4502/working/ExtremeWind/jobs/barra_points/barra_points_$i.sh

 qsub /home/548/ab4502/working/ExtremeWind/jobs/barra_points/barra_points_$i.sh

 done


