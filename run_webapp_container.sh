#!/bin/bash

CONTAINER=jicbioimage
docker run -p 80:5000 -it --rm -v `pwd`/scripts:/scripts -v `pwd`/output:/output $CONTAINER
