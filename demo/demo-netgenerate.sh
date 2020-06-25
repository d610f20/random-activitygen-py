#!/bin/sh
set -e

source venv/bin/activate
export SUMO_HOME=/home/user/projects/uni/d610f20/SUMO

rm "out/cities/*" || true

echo "====================="
echo ""
echo " NETGENERATE "
echo ""
echo "====================="

./in/generateNetLinux.sh 

echo "====================="
echo ""
echo " RANDOMACTIVITYGEN "
echo ""
echo "====================="
python ./randomActivityGen.py -n in/example.net.xml -s in/example.stat.xml -o out/example.stat.xml --display --display.size 1500

echo "====================="
echo ""
echo "    ACTIVITYGEN "
echo ""
echo "====================="
podman run -it -v ~/projects/uni/d610f20/random-activitygen-py/:/rap sumo activitygen -n /rap/in/cities/esbjerg.net.xml -s /rap/out/example.stat.xml -o /rap/out/example.rou.xml

echo "====================="
echo ""
echo "        SUMO "
echo ""
echo "====================="
podman run -it -e DISPLAY=:0 -v /tmp/.X11-unix:/tmp/.X11-unix -v ~/projects/uni/d610f20/random-activitygen-py/:/rap sumo-1.5 sumo-gui -n/rap/in/example.net.xml -r /rap/out/example.rou.xml --ignore-route-errors # -b 10000
