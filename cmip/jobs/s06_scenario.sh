#!/bin/bash

#PBS -P eg3 
#PBS -q hugemem
#PBS -l walltime=18:00:00,mem=1024GB 
#PBS -l ncpus=1
#PBS -o /home/548/ab4502/working/ExtremeWind/jobs/messages/s06_scenario.o 
#PBS -e /home/548/ab4502/working/ExtremeWind/jobs/messages/s06_scenario.e 
#PBS -l storage=gdata/eg3+gdata/ub4+gdata/ma05+gdata/du7+gdata/rr3+gdata/r87+gdata/fs38

source activate wrfpython3.6 

python working/ExtremeWind/cmip/cmip_scenario.py -p s06 -e rcp85 --force_compute True

