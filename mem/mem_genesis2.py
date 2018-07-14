import magma as m
from common.genesis_wrapper import run_genesis

import argparse


def define_mem_genesis2(data_width=16, data_depth=1024,
                        files=["mem/genesis/input_sr.vp",
                               "mem/genesis/output_sr.vp",
                               "mem/genesis/linebuffer_control.vp",
                               "mem/genesis/fifo_control.vp",
                               "mem/genesis/mem.vp",
                               "mem/genesis/memory_core.vp"]):
    parameters = {
        "dwidth": data_width,
        "ddepth": data_depth
    }
    outfile = run_genesis("memory_core", files, parameters)
    if outfile is None:
        return None
    return m.DefineFromVerilogFile(outfile)[0]


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("in_file_or_files",
                        help="file or list of files for memory",
                        nargs="+")
    parser.add_argument("--data-width", type=int, default=16)
    parser.add_argument("--data-depth", type=int, default=1024)
    return parser


def main(args):
    memory_core = define_mem_genesis2(args.data_width, args.data_depth,
                                      args.in_file_or_files)
    print(memory_core)


if __name__ == "__main__":
    """
    This program generates the verilog for the memory core and parses it into a
    Magma circuit. The circuit declaration is printed at the end of the
    program.
    """
    # These functions are unit tested directly, so no need to cover them
    parser = create_parser()  # pragma: no cover
    main(parser.parse_args())  # pragma: no cover
