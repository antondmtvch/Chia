#!/bin/bash

MEMORY=10240
THREADS=6
BASE_DIR="/home/ant/chiapos-bin"
TEMPDIR="/tmp"
PLOTS_DIR="/media/ant/HDD1/plots"
NOW=$(date +"%Y%m%dT%H%M")
LOG_PATH="$BASE_DIR/log/$NOW-plot.log"

$BASE_DIR/ProofOfSpace -k 32 -f $PLOTS_DIR -r $THREADS -b $MEMORY -t $TEMPDIR -2 $TEMPDIR -u 1024 create | tee $LOG_PATH