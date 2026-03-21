#!/bin/bash
SPEED=${1:-4}
/usr/local/bin/elad-firmware + $SPEED
echo $SPEED > /tmp/elad_speed
