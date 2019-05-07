from memory_core import memory_core_genesis2
from memory_core.memory_core import gen_memory_core, Mode
import glob
import os
import shutil
import fault
import random
from hwtypes import BitVector
from gemstone.common.testers import ResetTester, ConfigurationTester
from memory_core.memory_core_magma import MemCore
from gemstone.common.testers import BasicTester
import magma
import canal
import coreir
from gemstone.generator.generator import Generator



def teardown_function():
    return


def est_main(capsys):
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
        "memory_core/genesis_new/doublebuffer_control.vp",
        "memory_core/genesis_new/sram_stub.vp"
    ]
    memory_core_genesis2.memory_core_wrapper.main(
        argv=argv, param_mapping=memory_core_genesis2.param_mapping)
    out, _ = capsys.readouterr()


class MemoryCoreTester(ResetTester, ConfigurationTester):
    def write(self, addr, data):
        #self.functional_model.write(addr, data)
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


def est_other():
  # Setup functional model
  DATA_DEPTH = 1024
  DATA_WIDTH = 16
  MemFunctionalModel = gen_memory_core(DATA_WIDTH, DATA_DEPTH)
  mem_functional_model_inst = MemFunctionalModel()


  mem_core = MemCore(64,16,512,2)
  print(mem_core.ports)
  circuit = mem_core.circuit()
#  tester = ConfigurationTester(circuit, circuit.clk_in, circuit.reset)
#  tester = fault.Tester(circuit, circuit.clk_in)
  tester = MemoryCoreTester(circuit, clock=circuit.clk_in,
                              functional_model=mem_functional_model_inst)
  tester.poke(circuit.reset, 1)
  tester.poke(circuit.reset, 0)
  #tester.zero_inputs()
  tester.step(2)
  tester.poke(circuit.config_en_db, 1)
  tester.step(5)
  tester.poke(circuit.config_en_db, 0)

  tempdir = "tests/test_interconnect/build"
  for genesis_verilog in glob.glob("genesis_verif/*.*"):
                 shutil.copy(genesis_verilog, tempdir)
  tester.compile_and_run(target="verilator",
                                magma_output="coreir-verilog",
                                directory=tempdir,
                              flags=["-Wno-fatal --trace"])

def dbd_basic():

    db_basic(0,1,2,1,1,1,3,3,3)
    db_basic(1,0,2,1,1,1,3,3,3)
    db_basic(2,1,0,1,1,1,3,3,3)
    db_basic(0,2,1,1,1,1,3,3,3)
    db_basic(0,1,2,2,1,1,3,3,3)
    db_basic(0,1,2,1,2,1,3,3,3)
    db_basic(0,1,2,1,1,2,3,3,3)
    db_basic(0,1,2,1,1,2,3,3,3)


# @pytest.mark.parametrize("order1",[])
def db_basic(order0,order1,order2,stride0,stride1,stride2,size0,size1,size2):
    generator = memory_core_genesis2.memory_core_wrapper.generator(
        param_mapping=memory_core_genesis2.param_mapping)
    Mem = generator()  # Using default params
    for genesis_verilog in glob.glob("genesis_verif/*.v"):
        shutil.copy(genesis_verilog, "tests/test_memory_core/build")


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

    mode = 3 # DB
    tile_enable = 1
    depth = 50
    config_data = 3 | (tile_enable << 2) | (depth << 3)
    config_addr = BitVector(0, 32)
    tester.configure(config_addr, BitVector(config_data, 32))

    # Now configure the db - then write 1-27
    tester.poke(Mem.config_en, 0)
    tester.poke(Mem.config_en_db, 1)
    tester.poke(Mem.config_write, 1)
    tester.eval()
    config_data = 3
    config_addr = BitVector(0, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = stride0
    config_addr = BitVector(1, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = order0
    config_addr = BitVector(2, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = size0
    config_addr = BitVector(3, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = stride1
    config_addr = BitVector(4, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = order1
    config_addr = BitVector(5, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = size1
    config_addr = BitVector(6, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = stride2
    config_addr = BitVector(7, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = order2
    config_addr = BitVector(8, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.step()
    config_data = size2
    config_addr = BitVector(9, 32)
    tester.configure(config_addr, BitVector(config_data, 32))
    tester.poke(Mem.config_en, 0)
    tester.step()


    tester.poke(Mem.config_en_db,0)
    tester.poke(Mem.clk_in, 0)
    tester.eval()

    for i in range(27):
      tester.write(0,(i+1))
    tester.poke(Mem.clk_in,0)
    tester.poke(Mem.switch_db, 1)
    tester.eval()
    tester.poke(Mem.clk_in, 1)
    tester.eval()
    tester.poke(Mem.clk_in, 0)
    tester.poke(Mem.switch_db, 0)
    tester.eval()
    for i in range(27):
      tester.step(2)
      tester.eval()
      tester.print(Mem.data_out)


    print(str(order0) + " " + str(order1) + " " + str(order2) + " " + str(stride0) + " " + str(stride1) + " " + str(stride2) + " " + str(size0) + " " + str(size1) + " " + str(size2))
    tester.compile_and_run(directory="tests/test_memory_core/build",
                           magma_output="verilog",
                           target="verilator",
                           flags=["-Wno-fatal --trace"])
    print(str(order0) + " " + str(order1) + " " + str(order2) + " " + str(stride0) + " " + str(stride1) + " " + str(stride2) + " " + str(size0) + " " + str(size1) + " " + str(size2))


def sram_basic():
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
    for addr in addrs:
        print(str(addr))
        tester.read(addr)

    for i in range(num_writes):
        addr = get_fresh_addr(addrs)
        tester.read_and_write(addr, random.randint(0, (1 << 10)))
        tester.read(addr)

    tester.compile_and_run(directory="tests/test_memory_core/build",
                           magma_output="verilog",
                           target="verilator",
                           flags=["-Wno-fatal --trace"])
