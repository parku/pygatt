#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exceptions for pygatt Module.
"""

__author__ = 'Greg Albrecht <gba@orionlabs.co>'
__license__ = 'Apache License, Version 2.0'
__copyright__ = 'Copyright 2015 Orion Labs'


class BluetoothLEError(Exception):
    """Exception class for pygatt."""
    pass


class NotConnectedError(BluetoothLEError):
    pass


class NotificationTimeout(BluetoothLEError):
    pass


class NoResponseError(BluetoothLEError):
    pass
