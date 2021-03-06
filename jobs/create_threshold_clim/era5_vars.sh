#!/bin/bash

#PBS -P eg3
#PBS -q express
#PBS -l walltime=06:00:00,mem=64GB
#PBS -l ncpus=1
#PBS -o /home/548/ab4502/working/ExtremeWind/jobs/messages/event_analysis.o
#PBS -e /home/548/ab4502/working/ExtremeWind/jobs/messages/event_analysis.e
#PBS -lstorage=gdata/eg3

source activate wrfpython3.6

#python /home/548/ab4502/working/ExtremeWind/event_analysis.py t_totals 48.16 era5
#python /home/548/ab4502/working/ExtremeWind/event_analysis.py dcp 0.03 era5
python /home/548/ab4502/working/ExtremeWind/event_analysis.py ml_cape 0 era5
python /home/548/ab4502/working/ExtremeWind/event_analysis.py s06 0 era5

