import magma
from common.side_type import SideType
from generator.configurable import Configurable, ConfigurationType
from common.mux_wrapper import MuxWrapper
from generator.const import Const


def get_width(T):
    if isinstance(T, magma._BitKind):
        return 1
    if isinstance(T, magma.BitsKind):
        return T.N
    raise NotImplementedError(T, type(T))


class SB(Configurable):
    def __init__(self, inputs):
        super().__init__()

        self.all_inputs = inputs
        self.inputs = self.__organize_inputs(inputs)

        self.add_ports(
            north=SideType(5, (1, 16)),
            west=SideType(5, (1, 16)),
            south=SideType(5, (1, 16)),
            east=SideType(5, (1, 16)),
            clk=magma.In(magma.Clock),
            config=magma.In(ConfigurationType(8, 32)),
        )

        # TODO(rsetaluri): Clean up this logic.
        input_map = {}
        for i, input_ in enumerate(self.all_inputs):
            assert input_.type().isoutput()
            # TODO(rsetaluri): Name these inputs after the original inputs.
            port_name = f"core_out_{i}"
            self.add_port(port_name, magma.In(input_.type()))
            input_map[input_] = port_name

        sides = (self.north, self.west, self.south, self.east)
        self.muxs = self.__make_muxs(sides)
        for (side, layer, track), mux in self.muxs.items():
            idx = 0
            for side_in in sides:
                if side_in == side:
                    continue
                mux_in = getattr(side.I, f"layer{layer}")[track]
                self.wire(mux_in, mux.I[idx])
                idx += 1
            for input_ in self.inputs[layer]:
                port_name = input_map[input_]
                self.wire(self.ports[port_name], mux.I[idx])
                idx += 1
            mux_out = getattr(side.O, f"layer{layer}")[track]
            self.wire(mux.O, mux_out)

        for mux_idx, mux in enumerate(self.muxs.values()):
            config_name = f"sel_{mux_idx}"
            self.add_config(config_name, mux.sel_bits)
            self.wire(getattr(self, config_name), mux.S)
            self.registers[config_name].addr = mux_idx

        self.fanout(self.config.config_addr, self.registers.values())
        self.fanout(self.config.config_data, self.registers.values())

    def __organize_inputs(self, inputs):
        ret = {1: [], 16: []}
        for input_ in inputs:
            width = get_width(input_.type())
            assert width == 1 or width == 16
            ret[width].append(input_)
        return ret

    def __make_muxs(self, sides):
        height_per_layer = {
            1: 3 + len(self.inputs[1]),
            16: 3 + len(self.inputs[16]),
        }
        muxs = {}
        for side in sides:
            for layer, height in height_per_layer.items():
                for track in range(5):
                    muxs[(side, layer, track)] = MuxWrapper(height, layer)
        return muxs

    def name(self):
        name = "SB"
        for input_ in self.all_inputs:
            name += "_" + str(input_.type())
        return name.replace("(", "$").replace(")", "$")
