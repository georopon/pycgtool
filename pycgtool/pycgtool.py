import logging

from .frame import Frame
from .mapping import Mapping
from .bondset import BondSet
from .forcefield import ForceField
from .interface import Progress

logger = logging.getLogger(__name__)


def main(args, config):
    """
    Main function of the program PyCGTOOL.

    Performs the complete AA->CG mapping and outputs a files dependent on given input.

    :param args: Arguments from argparse
    :param config: Configuration dictionary
    """
    frame = Frame(gro=args.gro, xtc=args.xtc, itp=args.itp, frame_start=args.begin)

    if args.bnd:
        bonds = BondSet(args.bnd, config)
        logger.info("Bond measurements will be made")
    else:
        logger.info("Bond measurements will not be made")

    if args.map:
        mapping = Mapping(args.map, config, itp=args.itp)
        cgframe = mapping.apply(frame, exclude={"SOL"})
        cgframe.output(config.output_name + ".gro", format=config.output)
        logger.info("Mapping will be performed")
    else:
        logger.info("Mapping will not be performed")

    # Main loop - perform mapping and measurement on every frame in XTC
    def main_loop():
        nonlocal cgframe
        if not frame.next_frame():
            return False
        if args.map:
            cgframe = mapping.apply(frame, cgframe=cgframe, exclude={"SOL"})
            if config.output_xtc:
                cgframe.write_xtc(config.output_name + ".xtc")
        else:
            cgframe = frame
        if args.bnd:
            bonds.apply(cgframe)
        return True

    numframes = frame.numframes - args.begin if args.end == -1 else args.end - args.begin
    logger.info("Beginning analysis of {0} frames".format(numframes))
    Progress(numframes, dowhile=main_loop, quiet=args.quiet).run()

    if args.bnd:
        if args.map:
            logger.info("Beginning Boltzmann inversion")
            bonds.boltzmann_invert(progress=True)
            if config.output_forcefield:
                logger.info("Creating GROMACS forcefield directory")
                ff = ForceField("ff" + config.output_name + ".ff")
                ff.write_rtp(config.output_name + ".rtp", mapping, bonds)
                logger.info("GROMACS forcefield directory created")
            else:
                bonds.write_itp(config.output_name + ".itp", mapping=mapping)

        if config.dump_measurements:
            logger.info("Dumping bond measurements to file")
            bonds.dump_values(config.dump_n_values)


def map_only(args, config):
    """
    Perform AA->CG mapping and output coordinate file.

    :param args: Program arguments
    :param config: Object containing run options
    """
    frame = Frame(gro=args.gro, xtc=args.xtc)
    mapping = Mapping(args.map, config)
    cgframe = mapping.apply(frame, exclude={"SOL"})
    cgframe.output(config.output_name + ".gro", format=config.output)

    if args.xtc and (config.output_xtc or args.outputxtc):
        # Main loop - perform mapping and measurement on every frame in XTC
        def main_loop():
            nonlocal cgframe
            if not frame.next_frame():
                return False
            cgframe = mapping.apply(frame, cgframe=cgframe, exclude={"SOL"})
            cgframe.write_xtc(config.output_name + ".xtc")
            return True

        numframes = frame.numframes - args.begin if args.end == -1 else args.end - args.begin
        logger.info("Beginning analysis of {0} frames".format(numframes))
        Progress(numframes, dowhile=main_loop, quiet=args.quiet).run()

