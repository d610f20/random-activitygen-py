#!/bin/bash

"$SUMO_HOME"/bin/netgenerate --rand --random -o example.net.xml --rand.iterations=200 --roundabouts.guess=true --sidewalks.guess=true --crossings.guess=true --tls.guess=true --tls.guess.threshold=50