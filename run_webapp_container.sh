#!/bin/bash

CONTAINER=leaf-cell-polarisation-tensor
docker run -p 80:5000 -it --rm -v `pwd`/scripts:/scripts -v `pwd`/output:/output $CONTAINER
