#!/bin/bash

#PBS -P eg3 
#PBS -q hugemem
#PBS -l walltime=36:00:00,mem=1024GB
#PBS -l ncpus=1
#PBS -o /home/548/ab4502/working/ExtremeWind/jobs/messages/wrf_python_ACCESS-CM2_1960_1980.o 
#PBS -e /home/548/ab4502/working/ExtremeWind/jobs/messages/wrf_python_ACCESS-CM2_1960_1980.e 
#PBS -l storage=gdata/eg3+gdata/ub4+gdata/ma05+gdata/du7+gdata/rr3+gdata/r87+gdata/fs38
 
#Set up conda/shell environments 
source activate wrfpython3.6 

d=1960-01-01
while [ "$d" != 1980-01-01 ]; do

	start_time=$(date -d "$d" +%Y)"010100"
	end_time=$(date -d "$d + 9 year"  +%Y)"123118"

	python /home/548/ab4502/working/ExtremeWind/wrf_non_parallel.py -m ACCESS-CM2 -r aus -t1 $start_time -t2 $end_time --issave True --outname ACCESS-CM2_historical_r1i1p1f1 -e historical --ens r1i1p1f1 --group CSIRO-ARCCSS

	d=$(date -I -d "$d + 10 year")

done
