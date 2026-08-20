#!/usr/bin/env python3
"""Stream valid v1.1 controlled-stop command snapshots for bench testing."""

import socket
import struct
import sys
import time
import zlib


def build_registers(sequence: int, session: int, heartbeat: int, command: int,
                    monotonic_ms: int, profile: str) -> list[int]:
    steering_words = (0x7FC0, 0x0000) if profile == "nan" else (0xBE80, 0x0000)
    speed_words = (0x4040, 0x0000) if profile == "range" else (0x0000, 0x0000)
    command_flags = 0x0085 if profile == "bad-flags" else 0x0005
    protocol_minor = 0x0000 if profile == "wrong-minor" else 0x0001
    validity_words = (0x0000, 0x0258) if profile == "validity" else (0x0000, 0x00FA)
    registers = [
        0x5243, 0x0001, protocol_minor, 0x0040,
        (sequence >> 16) & 0xFFFF, sequence & 0xFFFF,
        (session >> 16) & 0xFFFF, session & 0xFFFF,
        (heartbeat >> 16) & 0xFFFF, heartbeat & 0xFFFF,
        (command >> 16) & 0xFFFF, command & 0xFFFF,
        (monotonic_ms >> 16) & 0xFFFF, monotonic_ms & 0xFFFF,
        0x0003, command_flags,        # CONTROLLED_STOP
        speed_words[0], speed_words[1],
        steering_words[0], steering_words[1],
        0x3F00, 0x0000,              # acceleration 0.5
        0x3FA0, 0x0000,              # deceleration 1.25
        0x3ECC, 0xCCCD,              # steering rate 0.4
        0x4000, 0x0000,              # mission speed limit 2.0
        validity_words[0], validity_words[1],
    ]
    registers.extend([0] * 30)
    if profile == "reserved":
        registers[30] = 1
    payload = b"".join(struct.pack(">H", value) for value in registers)
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    if profile == "bad-crc":
        crc ^= 1
    end_sequence = (sequence + 1) & 0xFFFFFFFF if profile == "torn" else sequence
    registers.extend([(crc >> 16) & 0xFFFF, crc & 0xFFFF,
                      (end_sequence >> 16) & 0xFFFF, end_sequence & 0xFFFF])
    return registers


def send_fc16(connection: socket.socket, transaction: int, registers: list[int]) -> None:
    values = b"".join(struct.pack(">H", value) for value in registers)
    pdu = struct.pack(">BHHB", 16, 0, len(registers), len(values)) + values
    request = struct.pack(">HHHB", transaction, 0, len(pdu) + 1, 1) + pdu
    connection.sendall(request)
    header = recv_exact(connection, 7)
    response_tid, protocol_id, length, unit_id = struct.unpack(">HHHB", header)
    payload = recv_exact(connection, length - 1)
    if response_tid != transaction or protocol_id != 0 or unit_id != 1:
        raise RuntimeError("invalid MBAP response")
    if payload[0] & 0x80:
        raise RuntimeError(f"Modbus exception function=0x{payload[0]:02X} code=0x{payload[1]:02X}")
    function, start, written = struct.unpack(">BHH", payload)
    if function != 16 or start != 0 or written != 64:
        raise RuntimeError("invalid FC16 acknowledgement")


def recv_exact(connection: socket.socket, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = connection.recv(length - len(chunks))
        if not chunk:
            raise ConnectionError("connection closed before complete response")
        chunks.extend(chunk)
    return bytes(chunks)


def main() -> int:
    if len(sys.argv) not in (2, 3, 4):
        print("usage: stream_orin_command_fc16.py HOST [DURATION_SECONDS] "
              "[normal|freeze-command|nan|range|bad-flags|validity|"
              "bad-crc|wrong-minor|torn|reserved]")
        return 2

    host = sys.argv[1]
    duration = float(sys.argv[2]) if len(sys.argv) >= 3 else 300.0
    profile = sys.argv[3] if len(sys.argv) == 4 else "normal"
    sessions = {
        "normal": 0x11223344,
        "freeze-command": 0x22334455,
        "nan": 0x33445566,
        "range": 0x44556677,
        "bad-flags": 0x55667788,
        "validity": 0x66778899,
        "bad-crc": 0x778899AA,
        "wrong-minor": 0x8899AABB,
        "torn": 0x99AABBCC,
        "reserved": 0xAABBCCDD,
    }
    if profile not in sessions:
        raise ValueError(f"unknown profile: {profile}")
    freeze_command = profile == "freeze-command"
    session = sessions[profile]
    sequence = 1
    heartbeat = 1
    command = 1
    transaction = 1
    start_time = time.monotonic()
    sent = 0

    with socket.create_connection((host, 502), timeout=3.0) as connection:
        connection.settimeout(3.0)
        while time.monotonic() - start_time < duration:
            monotonic_ms = int((time.monotonic() - start_time) * 1000) & 0xFFFFFFFF
            registers = build_registers(
                sequence, session, heartbeat, command, monotonic_ms, profile)
            send_fc16(connection, transaction, registers)
            sent += 1
            sequence = (sequence + 1) & 0xFFFFFFFF or 1
            heartbeat = (heartbeat + 1) & 0xFFFFFFFF or 1
            if not freeze_command:
                command = (command + 1) & 0xFFFFFFFF or 1
            transaction = (transaction + 1) & 0xFFFF or 1
            time.sleep(0.1)

    print(f"stream complete host={host} session=0x{session:08X} sent={sent}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
