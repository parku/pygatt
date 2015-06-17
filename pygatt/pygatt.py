from __future__ import print_function

# from collections import defaultdict
from binascii import unhexlify
import logging
# import string
import time

from bled112_backend import BLED112Backend
from pygatt_constants import(
    BACKEND, DEFAULT_CONNECT_TIMEOUT_S, LOG_LEVEL, LOG_FORMAT
)


class BluetoothLEDevice(object):
    """
    Interface for a Bluetooth Low Energy device that can use either the Bluegiga
    BLED112 (cross platform) or GATTTOOL (Linux only) as the backend.
    """
    def __init__(self, mac_address, backend=BACKEND['GATTTOOL'], logfile=None,
                 serial_port=None, delete_backend_bonds=True):
        """
        Initialize.

        mac_address -- a string containing the mac address of the BLE device in
                       the following format: "XX:XX:XX:XX:XX:XX"
        backend -- backend to use. One of pygatt.constants.backend.
        logfile -- the file in which to write the logs.
        serial_port -- the serial port to which the BLED112 is connected.
        delete_backend_bonds -- delete the bonds stored on the backend so that
                                bonding does not inadvertently take place.
        """
        # Initialize
        self._backend_type = None
        self._backend_type
        self._callbacks = {
            # uuid_str: func,
        }

        # Set up logging
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(LOG_LEVEL)
        if logfile is not None:
            handler = logging.FileHandler(logfile)
        else:  # print to stderr
            handler = logging.StreamHandler()
        formatter = logging.Formatter(fmt=LOG_FORMAT)
        handler.setLevel(LOG_LEVEL)
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)

        # Select backend, store mac address, optional delete bonds
        if backend == BACKEND['BLED112']:
            self._logger.info("pygatt[BLED112]")
            if serial_port is None:
                raise ValueError("serial_port %s", serial_port)
            self._backend = BLED112Backend(serial_port, loghandler=handler,
                                           loglevel=LOG_LEVEL)
            self._mac_address = bytearray(
                [int(b, 16) for b in mac_address.split(":")])
            self._backend.delete_stored_bonds()
        elif backend == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise ValueError("backend", backend)
        self._backend_type = backend

    def bond(self):
        """
        Securely Bonds to the BLE device.
        """
        self._logger.info("bond")
        if self._backend_type == BACKEND['BLED112']:
            self._backend.bond()
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def connect(self, timeout=DEFAULT_CONNECT_TIMEOUT_S):
        """
        Connect to the BLE device.

        timeout -- the length of time to try to establish a connection before
                   returning.

        Returns True if the connection was made successfully.
        Returns False otherwise.
        """
        self._logger.info("connect")
        if self._backend_type == BACKEND['BLED112']:
            return self._backend.connect(self._mac_address, timeout=timeout)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def char_read(self, uuid):
        """
        Reads a Characteristic by UUID.

        uuid -- UUID of Characteristic to read as a string.

        Returns a bytearray containing the characteristic value on success.
        Returns None on failure.
        """
        self._logger.info("char_read %s", uuid)
        if self._backend_type == BACKEND['BLED112']:
            handle = self._get_handle(uuid)
            if handle is None:
                return None
            return self._backend.char_read(handle)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def char_write(self, uuid_write, value, wait_for_response=False,
                   num_packets=0, uuid_recv=None):
        """
        Writes a value to a given characteristic handle.

        uuid -- the UUID of the characteristic to write to.
        value -- the value as a bytearray to write to the characteristic.
        wait_for_response -- wait for notifications/indications after writing.
        num_packets -- the number of notification/indication packets to wait
                       for.
        uuid_recv -- the UUID for the characteritic that will send the
                     notification/indication packets.

        Returns True on success.
        Returns False otherwise.
        """
        self._logger.info("char_write %s", uuid_write)
        # Validate arguments
        if wait_for_response and (num_packets <= 0):
            raise ValueError("num_packets must be greater than 0")

        # Write to the characteristic
        if self._backend_type == BACKEND['BLED112']:
            handle_write = self._get_handle(uuid_write)
            handle_recv = self._get_handle(uuid_recv)
            ret = self._backend.char_write(handle_write, value)
            if not ret:  # write failed
                return False
            if wait_for_response:
                # Wait for num_packets notifications on the receive
                #   characteristic
                while (len(self._backend.notifications[handle_recv]) <
                       num_packets):
                    time.sleep(0.25)  # busy wait
                # Assemble notification values into one bytearray and delete
                #   notification
                value_list = []
                for i in range(0, num_packets):
                    val = self._backend.notifications[handle_recv][0]
                    value_list += [b for b in val]
                    self._backend.notifications[handle_recv].pop(0)
                # Callback for notifications
                if uuid_recv in self._callbacks:
                    for cb in self._callbacks[uuid_recv]:
                        cb(bytearray(value_list))
            return True
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def encrypt(self):
        """
        Form an encrypted, but not bonded, connection.
        """
        self._logger.info("encrypt")
        if self._backend_type == BACKEND['BLED112']:
            self._backend.encrypt()
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def exit(self):
        """
        Cleans up. Run this when done using the BluetoothLEDevice object.
        """
        self._logger.info("exit")
        if self._backend_type == BACKEND['BLED112']:
            self._backend.disconnect()
            self._backend.stop()
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def get_rssi(self):
        """
        Get the receiver signal strength indicator (RSSI) value from the BLE
        device.

        Returns the RSSI value on success.
        Returns None on failure.
        """
        self._logger.info("get_rssi")
        if self._backend_type == BACKEND['BLED112']:
            # The BLED112 has some strange behavior where it will return 25 for
            # the RSSI value sometimes... Try a maximum of 3 times.
            for i in range(0, 3):
                rssi = self._backend.get_rssi()
                if rssi != 25:
                    return rssi
                time.sleep(0.1)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def run(self):
        """
        Run a background thread to listen for notifications.
        """
        self._logger.info("run")
        if self._backend_type == BACKEND['BLED112']:
            # Nothing to do
            pass
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def stop(self):
        """
        Stop the backgroud notification handler in preparation for a disconnect.
        """
        self._logger.info("stop")
        if self._backend_type == BACKEND['BLED112']:
            # Nothing to do
            pass
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def subscribe(self, uuid, callback=None, indication=False):
        """
        Enables subscription to a Characteristic with ability to call callback.

        uuid -- UUID as a string of the characteristic to subscribe to.
        callback -- function to be called when a notification/indication is
                    received on this characteristic.
        indication -- use indications (requires application ACK) rather than
                      notifications (does not requrie application ACK).
        """
        self._logger.info("subscribe to %s with callback %s. indicate = %d",
                          uuid, callback.__name__, indication)
        if self._backend_type == BACKEND['BLED112']:
            self._backend.subscribe(self._uuid_bytearray(uuid),
                                    indicate=indication)
            if callback is not None:
                if uuid not in self._callbacks:
                    self._callbacks[uuid] = []
                self._callbacks[uuid].append(callback)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def _get_handle(self, uuid):
        """
        Get the handle associated with the UUID.

        uuid -- a UUID in string format.
        """
        self._logger.info("_get_handle %s", uuid)
        uuid = self._uuid_bytearray(uuid)
        if self._backend_type == BACKEND['BLED112']:
            return self._backend.get_handle(uuid)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def _uuid_bytearray(self, uuid):
        """
        Turns a UUID string in the format "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
        to a bytearray.

        uuid -- the UUID to convert.

        Returns a bytearray containing the UUID.
        """
        self._logger.info("_uuid_bytearray %s", uuid)
        return unhexlify(uuid.replace("-", ""))

# FIXME going to use these?
    def _expect(self, expected):  # timeout=pygatt.constants.DEFAULT_TIMEOUT_S):
        """We may (and often do) get an indication/notification before a
        write completes, and so it can be lost if we "expect()"'d something
        that came after it in the output, e.g.:

        > char-write-req 0x1 0x2
        Notification handle: xxx
        Write completed successfully.
        >

        Anytime we expect something we have to expect noti/indication first for
        a short time.
        """
        if self._backend_type == BACKEND['BLED112']:
            raise NotImplementedError("backend", self._backend_type)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)

    def _handle_notification(self, msg):
        """
        Receive a notification from the connected device and propagate the value
        to all registered callbacks.
        """
        if self._backend_type == BACKEND['BLED112']:
            raise NotImplementedError("backend", self._backend_type)
        elif self._backend_type == BACKEND['GATTTOOL']:
            raise NotImplementedError("TODO")
        else:
            raise NotImplementedError("backend", self._backend_type)
