#!/bin/bash

#PBS -P eg3
#PBS -q express
#PBS -l walltime=24:00:00,mem=64GB 
#PBS -l ncpus=16
#PBS -o /home/548/ab4502/working/ExtremeWind/jobs/messages/logit_era5_aws.o
#PBS -e /home/548/ab4502/working/ExtremeWind/jobs/messages/logit_era5_aws.e
#PBS -l storage=gdata/eg3+gdata/ub4+gdata/ma05
#PBS -l place=pack:exclhost

source activate wrfpython3.6

python /home/548/ab4502/working/ExtremeWind/jobs/logit_selection/logit_era5_aws.py

