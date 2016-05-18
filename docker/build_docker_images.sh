!#/bin/bash

IMAGE_NAME=leaf-cell-polarisation-tensor

cp ../requirements.txt $IMAGE_NAME
cd $IMAGE_NAME
docker build -t $IMAGE_NAME .
cd ../
