#!/usr/bin/env python3
"""Minimal dependency-free Modbus TCP FC03 bench probe."""

import socket
import struct
import sys


def main() -> int:
    if len(sys.argv) not in (2, 4):
        print("usage: test_orin_modbus_fc03.py HOST [START QUANTITY]")
        return 2

    host = sys.argv[1]
    start = int(sys.argv[2], 0) if len(sys.argv) == 4 else 0
    quantity = int(sys.argv[3], 0) if len(sys.argv) == 4 else 16
    transaction_id = 1
    unit_id = 1

    if not 0 <= start <= 0xFFFF or not 1 <= quantity <= 125:
        raise ValueError("invalid FC03 start/quantity")

    pdu = struct.pack(">BHH", 3, start, quantity)
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
    if payload[0] != 3 or payload[1] != quantity * 2:
        raise RuntimeError("invalid FC03 response length")

    registers = list(struct.unpack(f">{quantity}H", payload[2:]))
    print(f"FC03 OK host={host} start={start} quantity={quantity}")
    print("registers=" + " ".join(f"{value:04X}" for value in registers))
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
