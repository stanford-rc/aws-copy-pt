# -*- coding: utf-8- -*-
# vim: ts=4 sw=4 noet

# Database code!

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


import aiosqlite
import functools
import os
import pathlib
import sys
from typing import Optional

from acp.logging import *


# The SQLite application ID is a 32-bit signed big-endian integer.
# It's based off the string 'acp\0', encoded as follows:
# struct.unpack('>i', struct.pack('cccc', b'a', b'c', b'p', b'\0'))[0]
APPLICATION_ID = 1633906688


# Memoized function to get the DB path
@functools.cache
def db_path() -> pathlib.Path:
	"""Get the database path.

	If the user has set an explicit database path in the `$ACP_DB_HOME`
	environment variable, then the database path is `$ACP_DB_HOME/db.sqlite3.
	Otherwise, default to `$XDG_DATA_HOME/acp/db.sqlite3`.  If `$XDG_DATA_HOME`
	doesn't exist, then use `$HOME/.local/share/acp/db.sqlite3`.  If `$HOME`
	does not exist, then the path used is `~/.local/share/acp/db.sqlite3`.

	If `~` is the first component of the path, then the OS is queried to
	resolve it to an absolute path.

	If parent directories do not exist, they are created.  No explicit
	permissions will be specified (the umask will effectively set permissions).

	This function is memoized, so the checks only happen on the first call, and
	the result is cached.  All subsequent calls (within this run of the
	program) will use the cached result.

	:return: The path to the database file.

	:raise FileExistsError: The path exists, and is a file.
	"""

	# First preference, use ACP_DB_HOME.
	if 'ACP_DB_HOME' in os.environ:
		pathdir = pathlib.Path(os.environ('ACP_DB_HOME'))
		debug(f"Using ACP_DB_HOME: {pathdir}")

		# Check if we have `~` in the path, and (if yes) resolve
		if pathdir.parts[0] == '~':
			pathdir = pathdir.expanduser()
			debug(f"Expanded ACP_DB_HOME to {pathdir}")

	# If that doesn't exist, check for XDG_DATA_HOME
	# (See the XDG Base Directory Specification)
	elif 'XDG_DATA_HOME' in os.environ:
		pathdir = pathlib.Path(os.environ('XDG_DATA_HOME')) / 'acp'
		debug(f"Using XDG_DATA_HOME: {pathdir}")
	
	# If that doesn't exist, check for HOME, and build a path
	elif 'HOME' in os.environ:
		pathdir = pathlib.Path(os.environ['HOME']) / '.local' / 'share' / 'acp'
		debug(f"Using HOME: {pathdir}")

	# If _that_ doesn't exist, then resolve our homedir, and build a path.
	# NOTE: This is a very weird situation, and should be warned about.
	# $HOME is required per POSIX.1-2017 Section 8.3.
	else:
		warning('Your environment is not setting the $HOME environment variable.')
		pathdir = pathlib.Path.home() / '.local' / 'share' / 'acp'
		debug(f"Auto-detecting home: {pathdir}")

	# We have a base directory!

	# If the directory doesn't exist, make it.
	if not pathdir.exists():
		info(f"Creating directory {pathdir}")
		pathdir.mkdir(parents=True)

	# We now know that pathdir exists.  Make sure it's not a file.
	if not pathdir.is_dir():
		raise FileExistsError(f"{pathdir} is a file, not a directory.")

	# All done!
	return (pathdir / 'db.sqlite3')


# Open a new DB connection
async def open(
	path: Optional[pathlib.Path] = None,
) -> aiosqlite.Connection:
	"""Connect to the DB, preparing/upgrading it as needed

	:param path: The path to the database file.

	:raise sqlite3.DatabaseError: The path is not a SQLite database.
	"""

	# If we aren't given an explicit path, get it ourselves.
	if path is None:
		path = db_path()

	# Is this a new database?
	new_db = False
	if not path.exists():
		new_db = True

	# Connect to the DB
	debug(f"Connecting to DB at {path}")
	conn = await aiosqlite.connect(db_path())

	# Is this a new database?  If yes, init the application ID and version.
	if new_db:
		debug(f'New DB!  Setting application ID and user_version')
		await conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
		await conn.execute('PRAGMA user_version = 0')
	else:
		# Check the existing application ID to make sure it's our DB
		db_application_id = list(
			await conn.execute_fetchall('PRAGMA application_id')
		)[0][0]
		if db_application_id != APPLICATION_ID:
			raise KeyError(f"DB application ID {db_application_id} does not match expected {APPLICATION_ID}")

	# Call out to do any needed DB upgrades
	db_user_version = list(
		await conn.execute_fetchall('PRAGMA user_version')
	)[0][0]
	await _upgrade(conn, db_user_version)

	# Return the prepared DB connection
	return conn


# Upgrade a DB
async def _upgrade(
	conn: aiosqlite.Connection,
	user_version: int,
) -> None:
	"""Upgrade the DB, if needed.

	:param conn: An open DB connection.

	:param user_version: The current user_version.
	"""

	debug(f"DB version is {user_version}")

	# 0 -> 1: Add AWS and Globus credentials
	if user_version == 0:
		debug('Upgrading DB from 0 to 1')
		await conn.execute('''
CREATE TABLE cred_aws (
    key     TEXT  NOT NULL  PRIMARY KEY,
    secret  TEXT  NOT NULL
)
		''')
		await conn.execute('''
CREATE TABLE cred_globus (
    key	    TEXT  NOT NULL  PRIMARY KEY,
    json    TEXT  NOT NULL
)
		''')
		await conn.execute('PRAGMA user_version = 1')
		user_version = 1

	# No more upgrades to do!
	return
