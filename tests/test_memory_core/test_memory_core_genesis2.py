from memory_core import memory_core_genesis2
from memory_core.memory_core import gen_memory_core, Mode
import glob
import os
import shutil
import fault
import random
from hwtypes import BitVector
from gemstone.common.testers import ResetTester, ConfigurationTester


def teardown_function():
    return


def test_main(capsys):
    argv = [
        "--data_width", "64",
        "--data_depth", "128",
        "--num_banks", "2",
        "--word_width", "16",
        "memory_core/genesis_new/linebuffer_control.vp",
        "memory_core/genesis_new/fifo_control.vp",
        "memory_core/genesis_new/mem.vp",
        "memory_core/genesis_new/sram_control.vp",
        "memory_core/genesis_new/memory_core.vp",
        "memory_core/genesis_new/sram_stub.vp"
    ]
    memory_core_genesis2.memory_core_wrapper.main(
        argv=argv, param_mapping=memory_core_genesis2.param_mapping)
    out, _ = capsys.readouterr()


class MemoryCoreTester(ResetTester, ConfigurationTester):
    def write(self, addr, data):
        self.functional_model.write(addr, data)
        # \_
        self.poke(self._circuit.clk_in, 0)
        self.poke(self._circuit.wen_in, 1)
        self.poke(self._circuit.addr_in, addr)
        self.poke(self._circuit.data_in, data)
        self.eval()

        # _/
        self.poke(self._circuit.clk_in, 1)
        self.eval()
        self.poke(self._circuit.wen_in, 0)

    def read(self, addr):
        # \_
        self.poke(self._circuit.clk_in, 0)
        self.poke(self._circuit.wen_in, 0)
        self.poke(self._circuit.addr_in, addr)
        self.poke(self._circuit.ren_in, 1)
        self.eval()

        # _/
        self.poke(self._circuit.clk_in, 1)
        self.eval()
        self.poke(self._circuit.ren_in, 0)

        self.poke(self._circuit.clk_in, 0)
        self.eval()

        self.functional_model.read(addr)
        self.poke(self._circuit.clk_in, 1)
        self.eval()
        # Don't expect anything after for now
        self.functional_model.data_out = fault.AnyValue

    def read_and_write(self, addr, data):
        # \_
        self.poke(self._circuit.clk_in, 0)
        self.poke(self._circuit.ren_in, 1)
        self.poke(self._circuit.wen_in, 1)
        self.poke(self._circuit.addr_in, addr)
        self.poke(self._circuit.data_in, data)
        self.eval()

        # _/
        self.poke(self._circuit.clk_in, 1)
        self.eval()
        self.poke(self._circuit.wen_in, 0)
        self.poke(self._circuit.ren_in, 0)

        # \_
        self.poke(self._circuit.clk_in, 0)
        self.eval()
        self.poke(self._circuit.clk_in, 1)
        self.functional_model.read_and_write(addr, data)
        self.eval()


def test_sram_basic():
    generator = memory_core_genesis2.memory_core_wrapper.generator(
        param_mapping=memory_core_genesis2.param_mapping)
    Mem = generator()  # Using default params
    for genesis_verilog in glob.glob("genesis_verif/*.v"):
        shutil.copy(genesis_verilog, "tests/test_memory_core/build")

    # FIXME: HACK from old CGRA, copy sram stub
#    shutil.copy("memory_core/genesis_new/sram_stub.vp",
#                "tests/test_memory_core/build/sram_stub.vp")

    # Setup functional model
    DATA_DEPTH = 1024
    DATA_WIDTH = 16
    MemFunctionalModel = gen_memory_core(DATA_WIDTH, DATA_DEPTH)
    mem_functional_model_inst = MemFunctionalModel()

    tester = MemoryCoreTester(Mem, clock=Mem.clk_in,
                              functional_model=mem_functional_model_inst)
    tester.zero_inputs()
    tester.expect_any_outputs()

    tester.eval()

    tester.poke(Mem.clk_en, 1)

    tester.reset()

    mode = Mode.SRAM
    tile_enable = 1
    depth = 8
    config_data = mode.value | (tile_enable << 2) | (depth << 3)
    config_addr = BitVector(0, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    num_writes = 20
    memory_size = 1024

    def get_fresh_addr(reference):
        """
        Convenience function to get an address not already in reference
        """
        addr = random.randint(0, memory_size - 1)
        while addr in reference:
            addr = random.randint(0, memory_size - 1)
        return addr

    addrs = set()
    # Perform a sequence of random writes
    for i in range(num_writes):
        addr = get_fresh_addr(addrs)
        # TODO: Should be parameterized by data_width
        data = random.randint(0, (1 << 10))
        tester.write(addr, data)
        addrs.add(addr)

    # Read the values we wrote to make sure they are there
    print('Made it to here mek')
    for addr in addrs:
        print(str(addr))
        tester.read(addr)

    print('Made it to here mek2')
    for i in range(num_writes):
        addr = get_fresh_addr(addrs)
        tester.read_and_write(addr, random.randint(0, (1 << 10)))
        tester.read(addr)

    print('Made it to here mek end?')
    tester.compile_and_run(directory="tests/test_memory_core/build",
                           magma_output="verilog",
                           target="verilator",
                           flags=["-Wno-fatal --trace"])
