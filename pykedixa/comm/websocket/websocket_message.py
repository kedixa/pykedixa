import enum
import struct
from typing import Union

from ..basic import (
    MessageBase,
    CommunicateBase,
)

__all__ = [
    'WebSocketOpcode',
    'WebSocketFrame',
]


class WebSocketOpcode(enum.IntEnum):
    ContinuationFrame = 0x00
    TextFrame = 0x01
    BinaryFrame = 0x02
    ConnectionClose = 0x08
    Ping = 0x09
    Pong = 0x0A

    @classmethod
    def has_value(cls, value: int) -> bool:
        return value in cls._value2member_map_


class WebSocketFrame(MessageBase):
    def __init__(self, *,
            fin: int = 1,
            rsv: int = 0,
            opcode: Union[WebSocketOpcode, int] = WebSocketOpcode.TextFrame,
            mask: Union[int, None] = None,
            payload: bytes = bytes()):
        self.fin = fin
        self.rsv = rsv
        self.opcode = opcode
        self.mask = mask
        self.payload = payload

    @property
    def fin(self) -> int:
        return self._fin

    @property
    def rsv(self) -> int:
        return self._rsv

    @property
    def opcode(self) -> Union[WebSocketOpcode, int]:
        if WebSocketOpcode.has_value(self._opcode):
            return WebSocketOpcode(self._opcode)
        else:
            return self._opcode

    @property
    def mask(self) -> Union[int, None]:
        return self._mask

    @property
    def payload(self) -> bytes:
        return self._payload

    @fin.setter
    def fin(self, value: int):
        self._fin: int = value & 0x1

    @rsv.setter
    def rsv(self, value: int):
        self._rsv: int = value & 0x7

    @opcode.setter
    def opcode(self, value: Union[WebSocketOpcode, int]):
        self._opcode: int = int(value) & 0xf

    @mask.setter
    def mask(self, value: Union[int, None]):
        if isinstance(value, int):
            self._mask: Union[int, None] = value & 0xFFFFFFFF
        else:
            self._mask = None

    @payload.setter
    def payload(self, value: bytes):
        if not isinstance(value, bytes):
            value = bytes(value)
        self._payload: bytes = value

    @classmethod
    def _mask_data(cls, data: bytes, key: int) -> bytes:
        msk = struct.pack('>I', key)
        return bytes([data[i] ^ msk[i%4] for i in range(len(data))])

    async def encode(self, c: CommunicateBase):
        buf = bytearray()

        h = (self._fin << 7) | (self._rsv << 4) | (self._opcode)
        buf.append(h)

        h = 0 if self._mask is None else 0x80
        plen = len(self._payload)
        ex = bytes()

        if plen <= 126:
            h |= plen
        elif plen <= 0xFFFF:
            h |= 126
            ex = struct.pack('>H', plen)
        else:
            h |= 127
            ex = struct.pack('>Q', plen)

        buf.append(h)
        buf.extend(ex)

        if self._mask is not None:
            buf.extend(struct.pack('>I', self._mask))
            buf.extend(WebSocketFrame._mask_data(self._payload, self._mask))
        else:
            buf.extend(self._payload)

        await c.write_all(buf)

    async def decode(self, c: CommunicateBase):
        h = await c.read_exactly(2)
        self._fin = (h[0] >> 7) & 0x01
        self._rsv = (h[0] >> 4) & 0x07
        self._opcode = h[0] & 0x0f
        has_mask = (h[1] & 0x80) == 0x80
        plen = h[1] & 0x7f

        if plen == 126:
            x = await c.read_exactly(2)
            plen, = struct.unpack('>H', x)
        elif plen == 127:
            x = await c.read_exactly(4)
            plen, = struct.unpack('>Q', x)

        if has_mask:
            x = await c.read_exactly(4)
            self._mask, = struct.unpack('>I', x)
        else:
            self._mask = None

        data = await c.read_exactly(plen)
        if has_mask:
            # mask and unmask use same method
            self._payload = WebSocketFrame._mask_data(data, self._mask)
        else:
            self._payload = bytes(data)
