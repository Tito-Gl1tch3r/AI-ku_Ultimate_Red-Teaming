"""
Module containing custom exceptions for soSaver.

Provides specific exception types for various error scenarios that occur during application operation.
"""

from typing import Optional


class SOSaverError(Exception):
    """Base class for all soSaver exceptions."""

    def __init__(self, message: str = "An error occurred in soSaver."):
        """Initialize the base exception.

        Args:
            message: Error message to be displayed.
        """
        super().__init__(message)


class DeviceConnectionError(SOSaverError):
    """Error when connecting to an Android device."""

    def __init__(self, message: str = "Failed to connect to device.", device_id: Optional[str] = None):
        """Initialize device connection error.

        Args:
            message: Error message to be displayed.
            device_id: ID of the device that failed to connect.
        """
        if device_id:
            message = f"{message} (device: {device_id})"
        super().__init__(message)
        self.device_id = device_id


class ProcessAttachError(SOSaverError):
    """Error when attaching to a process."""

    def __init__(self, message: str = "Failed to attach to process.", target: Optional[str] = None):
        """Initialize process attach error.

        Args:
            message: Error message to be displayed.
            target: Target process that failed to attach.
        """
        if target:
            message = f"{message} (target: {target})"
        super().__init__(message)
        self.target = target


class ScriptLoadError(SOSaverError):
    """Error when loading or executing a Frida script."""

    def __init__(self, message: str = "Failed to load or execute script.", script_name: Optional[str] = None):
        """Initialize script load error.

        Args:
            message: Error message to be displayed.
            script_name: Name of the script that failed to load.
        """
        if script_name:
            message = f"{message} (script: {script_name})"
        super().__init__(message)
        self.script_name = script_name
