from memory_core import memory_core
from bit_vector import BitVector


def my_test_instance(data_width, data_depth):
    my_MemoryCore = memory_core.gen_memory_core(data_width, data_depth)
    mc = my_MemoryCore()



    # Simple SRAM tests
    mc.reset()

    mode = memory_core.Mode.SRAM
    tile_enable = 1
    depth = 8
    config_data = mode.value | (tile_enable << 2) | (depth << 3)
    config_addr = BitVector(0, 32)
    mc.configure(config_addr, BitVector(config_data, 32))

    mc.write(5, 42)
    mc.read(5)
    assert mc.data_out == 42


    # Simple FIFO tests
    mc.reset()
    mode = memory_core.Mode.FIFO
    config_data = mode.value | (tile_enable << 2) | (depth << 3)
    mc.configure(config_addr, BitVector(config_data, 32))

    mc.write(0, 8)
    mc.write(0, 42)
    mc.write(0, 123)

    mc.read(0)
    assert mc.data_out == 8

    mc.write(0, 4321)

    mc.read(0)
    assert mc.data_out == 42
    mc.read(0)
    assert mc.data_out == 123
    mc.read(0)
    assert mc.data_out == 4321



    # Try reading empty FIFO
    try:
        mc.read(0)
    except AssertionError:
        pass
    else:
        assert False, "Read should have failed"



    # try writing to full FIFO
    mc.reset()
    mode = memory_core.Mode.FIFO
    config_data = mode.value | (tile_enable << 2) | (depth << 3)
    mc.configure(config_addr, BitVector(config_data, 32))

    for i in range(data_depth):
        mc.write(0, i*3)
    for i in range(data_depth):
        mc.read(0)
        assert mc.data_out == i*3
    for i in range(data_depth):
        mc.write(0, i*3)

    try:
        mc.write(0, 0)
    except AssertionError:
        pass
    else:
        assert False, "Write should have failed"



def test_standard_size():
    my_test_instance(16, 1024)

