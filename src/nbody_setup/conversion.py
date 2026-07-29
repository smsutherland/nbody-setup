import typing as T
from enum import StrEnum, auto
from pathlib import Path


class IcFormat(StrEnum):
    Gadget1 = auto()

    def convert_to(self, to: "IcFormat", input_name: Path, output_name: Path):
        input_name = input_name.resolve()
        output_name = output_name.resolve()
        samefile = input_name == output_name

        match (self, to):
            case (IcFormat.Gadget1, IcFormat.Gadget1):
                if not samefile:
                    i = 0
                    while (input_file := input_name.with_suffix(f".{i}")).exists():
                        output_name.with_suffix(f".{i}").symlink_to(
                            input_file.relative_to(output_name.parent),
                        )
                        i += 1
            case _ as never:
                T.assert_never(never)
