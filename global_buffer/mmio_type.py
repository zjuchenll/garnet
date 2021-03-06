import magma


def MMIOType(addr_width, data_width):
    """
    This function returns a class (parameterized by @addr_width and
    @data_width) which can be used as the magma ports with these inputs
    and outputs
        1. rd_en
        2. rd_addr
        3. rd_data
        4. wr_en
        5. wr_addr
        6. wr_Data
    """

    _MMIOType = magma.Tuple(
        wr_en=magma.In(magma.Bit),
        wr_addr=magma.In(magma.Bits[addr_width]),
        wr_data=magma.In(magma.Bits[data_width]),
        rd_en=magma.In(magma.Bit),
        rd_addr=magma.In(magma.Bits[addr_width]),
        rd_data=magma.Out(magma.Bits[data_width]))

    return _MMIOType
