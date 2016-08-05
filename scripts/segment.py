import argparse


def generate_segmentations_from_microscope_image(input_file, wall_channel,
                                                 marker_channel):
    """Generate cell-segmentation.png and marker-segmentation.png files."""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help="Input microscope file.")
    parser.add_argument("-w", "--wall-channel",
                        default=1, type=int,
                        help="Wall channel (zero indexed)")
    parser.add_argument("-m", "--marker-channel",
                        default=0, type=int,
                        help="Marker channel (zero indexed)")

    args = parser.parse_args()

    generate_segmentations_from_microscope_image(args.input_file,
                                                 args.wall_channel,
                                                 args.marker_channel)


if __name__ == "__main__":
    main()
