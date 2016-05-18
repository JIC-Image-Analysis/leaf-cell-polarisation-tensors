#!/bin/bash

CONTAINER=leaf-cell-polarisation-tensor
docker run -it --rm -v `pwd`/data:/data -v `pwd`/scripts:/scripts -v `pwd`/output:/output $CONTAINER
