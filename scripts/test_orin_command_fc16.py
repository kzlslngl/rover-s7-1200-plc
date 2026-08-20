#!/usr/bin/env python3
"""Write the authoritative v1.1 controlled-stop command test vector."""

import socket
import struct
import sys
import zlib


PREFIX = [
    0x5243, 0x0001, 0x0001, 0x0040, 0x0000, 0x002A,
    0x0102, 0x0304, 0x0000, 0x0064, 0x0000, 0x0063,
    0x0001, 0xE240, 0x0003, 0x0005, 0x0000, 0x0000,
    0xBE80, 0x0000, 0x3F00, 0x0000, 0x3FA0, 0x0000,
    0x3ECC, 0xCCCD, 0x4000, 0x0000, 0x0000, 0x00FA,
]
EXPECTED_CRC = 0x5C224D43


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_orin_command_fc16.py HOST")
        return 2

    registers = PREFIX + ([0] * 30)
    wire = b"".join(struct.pack(">H", value) for value in registers)
    calculated_crc = zlib.crc32(wire) & 0xFFFFFFFF
    if calculated_crc != EXPECTED_CRC:
        raise RuntimeError(
            f"local vector CRC mismatch: 0x{calculated_crc:08X}"
        )
    registers.extend([EXPECTED_CRC >> 16, EXPECTED_CRC & 0xFFFF, 0x0000, 0x002A])

    host = sys.argv[1]
    transaction_id = 2
    unit_id = 1
    quantity = len(registers)
    values = b"".join(struct.pack(">H", value) for value in registers)
    pdu = struct.pack(">BHHB", 16, 0, quantity, len(values)) + values
    request = struct.pack(">HHHB", transaction_id, 0, len(pdu) + 1, unit_id) + pdu

    with socket.create_connection((host, 502), timeout=3.0) as connection:
        connection.sendall(request)
        header = recv_exact(connection, 7)
        response_tid, protocol_id, length, response_unit = struct.unpack(">HHHB", header)
        payload = recv_exact(connection, length - 1)

    if response_tid != transaction_id or protocol_id != 0 or response_unit != unit_id:
        raise RuntimeError("invalid MBAP response")
    if payload[0] & 0x80:
        raise RuntimeError(f"Modbus exception function=0x{payload[0]:02X} code=0x{payload[1]:02X}")
    function, start, written = struct.unpack(">BHH", payload)
    if function != 16 or start != 0 or written != quantity:
        raise RuntimeError("invalid FC16 acknowledgement")

    print(f"FC16 OK host={host} start=0 quantity={quantity}")
    print(f"sequence=42 crc=0x{EXPECTED_CRC:08X} mode=CONTROLLED_STOP flags=0x0005")
    return 0


def recv_exact(connection: socket.socket, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = connection.recv(length - len(chunks))
        if not chunk:
            raise ConnectionError("connection closed before complete response")
        chunks.extend(chunk)
    return bytes(chunks)


if __name__ == "__main__":
    raise SystemExit(main())
