# README

## Installation

Download the source code from GitHub:

https://github.com/JIC-Image-Analysis/leaf-cell-polarisation-tensors

This image analysis project has been setup to take advantage of a technology
known as Docker.

This means that you will need to:

1. Download and install the [Docker Toolbox](https://www.docker.com/products/docker-toolbox)
2. Build the local docker image:

```
$ cd docker
$ bash build_docker_images.sh
$ cd ../
```

## Automated tensor analysis

1. Put your image file, e.g. ``genotype1.tif`` into the ``data`` directory.
2. Start a docker session in the analysis container

```
$ bash run_analysis_container.sh
[root@25278c5a93ec /]#
```

3. Run the automated analysis script on the image

```
[root@25278c5a93ec /]# python /scripts/automated_analysis.py /data/genotype1.tif /output/genotype1
```


## Editing tensors

1. Start a docker session in the webapp continer

```
$ bash run_webapp_container.sh
[root@125b9dd8d3df /]#
```

2. Start the webapp

```
[root@125b9dd8d3df /]# python /scripts/webapp.py /output/genotype1/
```

3. Point a web browser at http://192.168.99.100/ and start editing
