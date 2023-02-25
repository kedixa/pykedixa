import io
from typing import Union, List

__all__ = [
    'file_loader',
    'mfile_loader'
]

def _file_loader(file: io.TextIOBase, batch_size: int) -> List[str]:
    lines = []
    for line in file:
        lines.append(line)
        if len(lines) >= batch_size:
            yield lines
            lines = []

    if len(lines) > 0:
        yield lines

def file_loader(file: Union[str, bytes, io.TextIOBase],
        batch_size: int = 64,
        *args, **kwargs):
    if isinstance(file, io.TextIOBase):
        yield from _file_loader(file, batch_size)
    else:
        with open(file, *args, **kwargs) as f:
            yield from _file_loader(f, batch_size)

def mfile_loader(files: List[Union[str, bytes, io.TextIOBase]],
        batch_size: int = 64,
        *args, **kwargs):
    for file in files:
        yield from file_loader(file, batch_size, *args, **kwargs)
