import magma as m
from gemstone.common.genesis_wrapper import GenesisWrapper, default_type_map
from gemstone.common.generator_interface import GeneratorInterface


"""
Defines the memory_core using genesis2.

`data_width`: width of an entry in the memory
`data_depth`: number of entries in the memory

Example usage:
    >>> memory_core = memory_core_wrapper.generator()(
            data_width=16, data_depth=1024)
"""
interface = GeneratorInterface()\

memory_stub_wrapper = GenesisWrapper(
    interface, "memory_stub", ["memory_core/genesis/tsmc_zone"],
    type_map={"CLK": m.In(m.Clock)}
	)


if __name__ == "__main__":
    """
    This program generates the verilog for the memory core and parses it into a
    Magma circuit. The circuit declaration is printed at the end of the
    program.
    """
    # These functions are unit tested directly, so no need to cover them
    memory_stub_wrapper.main(param_mapping=param_mapping)  # pragma: no cover
