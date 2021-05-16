#!/bin/bash

MEMORY=10240
THREADS=8
BASE_DIR="~/chiapos-bin"
TEMPDIR="/tmp"
PLOTS_DIR="/media/ant/HDD1/plots"
LOG_PATH="$BASE_DIR/log/$(date +"%Y%m%dT%H%M")-plot.txt"

$BASE_DIR/ProofOfSpace -k 32 -f $PLOTS_DIR -r $THREADS -b $MEMORY -t $TEMPDIR -2 $TEMPDIR -u 1024 create | tee $LOG_PATH