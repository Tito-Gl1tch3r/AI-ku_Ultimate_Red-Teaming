"""Request a new Tor circuit (NEWNYM via control port)."""

from __future__ import annotations

import asyncio

import structlog

logger = structlog.get_logger(__name__)


async def tor_new_identity(
    control_port: int = 9051,
    control_password: str = "",
) -> dict:
    """Request a new Tor circuit via the control port (NEWNYM signal).

    Args:
        control_port: Tor control port (default 9051)
        control_password: Tor control password (from torrc)

    Returns:
        Dictionary with success status and message.
    """
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", control_port)

        # Authenticate
        if control_password:
            writer.write(f'AUTHENTICATE "{control_password}"\r\n'.encode())
        else:
            writer.write(b"AUTHENTICATE\r\n")

        await writer.drain()
        response = await asyncio.wait_for(reader.read(100), timeout=5)

        if b"250" not in response:
            writer.close()
            return {
                "success": False,
                "message": "Authentication failed",
                "response": response.decode(),
            }

        # Request new identity
        writer.write(b"SIGNAL NEWNYM\r\n")
        await writer.drain()
        response = await asyncio.wait_for(reader.read(100), timeout=5)
        writer.close()

        success = b"250" in response
        return {
            "success": success,
            "message": "New identity requested" if success else "NEWNYM signal failed",
            "response": response.decode().strip(),
        }
    except ConnectionRefusedError:
        return {
            "success": False,
            "message": (
                f"Tor control port {control_port} is not accessible. "
                "Ensure Tor is running with ControlPort enabled."
            ),
        }
    except Exception as exc:
        return {"success": False, "message": str(exc)}
