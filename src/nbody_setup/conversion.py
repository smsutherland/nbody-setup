import typing as T
from enum import StrEnum, auto
from pathlib import Path

import h5py


class Format(StrEnum):
    Gadget1 = auto()
    GadgetHDF5 = auto()

    def convert_to(self, to: "Format", input_name: Path, output_name: Path):
        input_name = input_name.resolve()
        output_name = output_name.resolve()
        samefile = input_name == output_name

        match (self, to):
            case (Format.Gadget1, Format.Gadget1):
                if not samefile:
                    i = 0
                    while (input_file := input_name.with_suffix(f".{i}")).exists():
                        output_name.with_suffix(f".{i}").symlink_to(
                            input_file.relative_to(output_name.parent),
                        )
                        i += 1
            case (Format.GadgetHDF5, Format.Gadget1):
                raise NotImplementedError(
                    "GadgetHDF5 -> Gadget1 conversion not implemented"
                )
            case (Format.Gadget1, Format.GadgetHDF5):
                raise NotImplementedError(
                    "Gadget1 -> GadgetHDF5 conversion not implemented"
                )
            case (Format.GadgetHDF5, Format.GadgetHDF5):
                raise NotImplementedError(
                    "GadgetHDF5 -> GadgetHDF5 conversion not implemented"
                )
            case _:
                T.assert_never()

    def compress(
        self,
        input_name: Path,
        output_name: Path,
        pos_acc: int | None = None,
        vel_acc: int | None = None,
    ):
        match self:
            case Format.Gadget1:
                _compress_gadget1(input_name, output_name, pos_acc, vel_acc)
            case Format.GadgetHDF5:
                _compress_gadgethdf5(input_name, output_name, pos_acc, vel_acc)
            case _:
                T.assert_never()


def _compress_gadget1(
    input_name: Path,
    output_name: Path,
    pos_acc: int | None,
    vel_acc: int | None,
): ...


def _compress_gadgethdf5(
    input_name: Path,
    output_name: Path,
    pos_acc: int | None,
    vel_acc: int | None,
):
    with (
        h5py.File(input_name) as fin,
        h5py.File(output_name.with_suffix(".inprogress"), "w") as fout,
    ):
        fin.copy(fin["Header"], fout, "Header")

        for i in (1, 2):
            ptype = f"PartType{i}"
            if ptype not in fin:
                continue
            gin: h5py.Group = fin[ptype]
            gout: h5py.Group = fout.create_group(ptype)

            idsin: h5py.Dataset = gin["ParticleIDs"]
            idsout = gout.create_dataset(
                "ParticleIDs",
                idsin.shape,
                idsin.dtype,
                compression="gzip",
                compression_opts=6,
                shuffle=True,
                fletcher32=True,
                chunks=min(2**20, idsin.shape[0]),
            )
            for chunk in idsin.iter_chunks():
                idsout[chunk] = idsin[chunk]
            idsout.flush()

            posin = gin["Coordinates"]
            if pos_acc is not None:
                posout = gout.create_dataset(
                    "Coordinates",
                    posin.shape,
                    posin.dtype,
                    compression="gzip",
                    compression_opts=4,
                    shuffle=True,
                    chunks=(min(2**20, posin.shape[0]), 3),
                    scaleoffset=pos_acc,
                )
            else:
                posout = gout.create_dataset(
                    "Coordinates",
                    posin.shape,
                    posin.dtype,
                    compression="gzip",
                    compression_opts=4,
                    shuffle=True,
                    fletcher32=True,
                    chunks=(min(2**20, posin.shape[0]), 3),
                )
            for chunk in posin.iter_chunks():
                posout[chunk] = posin[chunk]
            posout.flush()

            velin = gin["Velocities"]
            if vel_acc is not None:
                velout = gout.create_dataset(
                    "Velocities",
                    velin.shape,
                    velin.dtype,
                    compression="gzip",
                    compression_opts=4,
                    shuffle=True,
                    chunks=(min(2**20, velin.shape[0]), 3),
                    scaleoffset=pos_acc,
                )
            else:
                velout = gout.create_dataset(
                    "Velocities",
                    velin.shape,
                    velin.dtype,
                    compression="gzip",
                    compression_opts=4,
                    shuffle=True,
                    fletcher32=True,
                    chunks=(min(2**20, velin.shape[0]), 3),
                )
            for chunk in velin.iter_chunks():
                velout[chunk] = velin[chunk]
            velout.flush()

    output_name.with_suffix(".inprogress").rename(output_name)
