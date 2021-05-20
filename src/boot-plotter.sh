#!/bin/bash

MEMORY=4096
THREADS=4
BASE_DIR="/home/ant/chiapos-bin"
TEMP_DIR="/tmp"
PLOTS_DIR="/media/ant/HDD1/plots"
NOW=$(date +"%Y%m%dT%H%M")
LOG_PATH="$BASE_DIR/log/$NOW-plot.log"

$BASE_DIR/ProofOfSpace -k 32 -f $PLOTS_DIR -r $THREADS -b $MEMORY -t $TEMP_DIR -2 $TEMP_DIR -u 1024 create | tee $LOG_PATH