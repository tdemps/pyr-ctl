#!/bin/bash

echo "nec rc-5" | sudo tee /sys/class/rc/rc1/protocols
# echo "sony" | sudo tee /sys/class/rc/rc1/protocols
#echo "lirc" | sudo tee /sys/class/rc/rc1/protocols