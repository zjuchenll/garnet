import metamapper as mm
from lassen.sim import gen_pe
import lassen.asm as asm
import coreir


class MapperWrapper:
    def __init__(self, context):
        self.context = context
        self.mapper = mm.PeakMapper(self.context, "lassen")
        self.mapper.add_io_and_rewrite("io1", 1, "io2f_1", "f2io_1")
        self.mapper.add_io_and_rewrite("io16", 16, "io2f_16", "f2io_16")
        self.pe = self.mapper.add_peak_primitive("PE", gen_pe)

        # Hack to speed up rewrite rules discovery.
        def bypass_mode(inst):
            return (
                    inst.rega == type(inst.rega).BYPASS and
                    inst.regb == type(inst.regb).BYPASS and
                    inst.regd == type(inst.regd).BYPASS and
                    inst.rege == type(inst.rege).BYPASS and
                    inst.regf == type(inst.regf).BYPASS
            )

        self.mapper.add_discover_constraint(bypass_mode)

        # TODO:
        #   manually define every primitive to enable fast mapping
        mult = self.__import("coreir", "mul")(width=16)
        self.mapper.add_rewrite_rule(mm.Peak1to1(
            mult,  # coreir module
            self.pe,  # coreir pe
            asm.umult0(),  # Instruction for PE
            dict(in0='data0', in1='data1', out="alu_res")  # port Mapping
        ))

        # just get const since const folding is not working in peak
        self.mapper.discover_peak_rewrite_rules(width=16,
                                                coreir_primitives=["const"])

    def map(self, app):
        return self.mapper.map_app(app)

    def __get_lib(self, lib):
        if lib in {"coreir", "mantle", "corebit"}:
            return self.context.get_namespace(lib)
        elif lib == "global":
            return self.context.global_namespace
        else:
            return self.context.load_library(lib)

    def __import(self, lib, name):
        return self.__get_lib(lib).generators[name]


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage:", sys.argv[0], "<design_top.json>", "<mapped.json>",
              file=sys.stderr)
        exit(1)
    app_ = sys.argv[1]
    output = sys.argv[2]
    context = coreir.Context()
    mapper = MapperWrapper(context)

    app_ = context.load_from_file(app_)
    mapped: coreir.Module = mapper.map(app_)
    mapped.save_to_file(output)
