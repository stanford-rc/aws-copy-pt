# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

# Logging handlers!

# © 2022 The Board of Trustees of the Leland Stanford Junior University
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import logging
import sys


# Export logging endpoints
__all__ = ['debug', 'info', 'warning', 'error']


# Have a logger for library stuff
lib_logger = logging.getLogger(__name__)

# Library messages go to stdout
lib_handler = logging.StreamHandler()
lib_logger.addHandler(lib_handler)

# Library messages show time, function, file, and message
lib_formatter = \
	logging.Formatter('%(asctime)s [%(filename)s:%(lineno)d] (%(funcName)s) %(message)s')
lib_handler.setFormatter(lib_formatter)

# Default logging level is WARNING for lib
lib_logger.setLevel(logging.DEBUG)

# These are the library logging endpoints
debug = lib_logger.debug
info = lib_logger.info
warning = lib_logger.warning
error = lib_logger.error
