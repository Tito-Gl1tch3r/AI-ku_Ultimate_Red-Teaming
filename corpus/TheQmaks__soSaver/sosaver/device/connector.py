"""
Module for connecting to Android devices and interacting with processes.

Provides classes and functions for device connection and
debugging processes through Frida.
"""

from typing import Optional, Union

import frida
from frida.core import Device, Session

from sosaver.utils.exceptions import DeviceConnectionError, ProcessAttachError
from sosaver.utils.logging import logger


class DeviceConnector:
    """
    Class for connecting to a device and attaching to a process.

    Provides device discovery, connection, and interaction
    with processes through Frida.
    """

    def __init__(self, target: Union[str, int]):
        """
        Initialize the device connection.

        Args:
            target: Target process name or PID
        """
        self.target = target
        self.device: Optional[Device] = None
        self.session: Optional[Session] = None

    def connect(self, device_id: Optional[str] = None, timeout: int = 5) -> Device:
        """
        Connect to a device.

        Args:
            device_id: Device identifier (if None, USB is used)
            timeout: Connection timeout in seconds

        Returns:
            Connected device object

        Raises:
            DeviceConnectionError: If failed to connect to the device
        """
        try:
            if device_id:
                logger.info(f"Connecting to device with ID {device_id}")
                self.device = frida.get_device(device_id, timeout)
            else:
                logger.info("Connecting to USB device")
                self.device = frida.get_usb_device(timeout)

            logger.debug(f"Successfully connected to device: {self.device.name} ({self.device.id})")
            return self.device

        except frida.TimedOutError as e:
            error_msg = "Timeout connecting to device"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg) from e

        except frida.InvalidArgumentError as e:
            error_msg = f"Invalid device identifier: {e}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg) from e

        except Exception as e:
            error_msg = f"Error connecting to device: {e}"
            logger.error(error_msg)
            raise DeviceConnectionError(error_msg) from e

    def attach_to_process(self, device_id: Optional[str] = None) -> Session:
        """
        Attach to the target process.

        Args:
            device_id: Device identifier (if None, USB is used)

        Returns:
            Frida session object

        Raises:
            ProcessAttachError: If failed to attach to the process
        """
        try:
            # Connect to the device if not already connected
            if not self.device:
                self.connect(device_id)

            if self.device is None:
                raise DeviceConnectionError("Device must be initialized")

            # Determine if the target process is a name or PID
            if isinstance(self.target, str):
                target_name = self.target

                # Check if the process is already running
                try:
                    pid = self.device.get_process(target_name).pid
                    logger.info(f"Process '{target_name}' is already running with PID: {pid}")
                except frida.ProcessNotFoundError:
                    # Try to launch the process if it's not running
                    logger.info(f"Launching process '{target_name}'")
                    pid = self.device.spawn([target_name])
                    logger.info(f"Process launched with PID: {pid}")

                    # Attach to the launched process
                    self.session = self.device.attach(pid)

                    # Resume the process
                    self.device.resume(pid)
                    logger.info("Process resumed")

                    return self.session

            else:  # PID
                pid = self.target
                logger.info(f"Attaching to process with PID {pid}")

            # Attach to the process
            self.session = self.device.attach(pid)
            logger.info(f"Process attached with PID: {pid}")
            return self.session

        except frida.ProcessNotFoundError as e:
            error_msg = f"Process {self.target} not found"
            logger.error(error_msg)
            raise ProcessAttachError(error_msg, str(self.target)) from e

        except frida.ServerNotRunningError as e:
            error_msg = "Frida server is not running on the device"
            logger.error(error_msg)
            raise ProcessAttachError(error_msg, str(self.target)) from e

        except Exception as e:
            error_msg = f"Error attaching to process: {e}"
            logger.error(error_msg)
            raise ProcessAttachError(error_msg, str(self.target)) from e
