# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

# CLI runner!

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


from __future__ import annotations

import asyncio
import os
import sys
from typing import NoReturn, Optional
import uuid

import acp.db
import acp.globus
from acp.logging import *


# The main that dumps us into the async world.
async def _main():
	# Let's start out with some setup!

	is_interactive = (True if sys.stdout.isatty() else False)
	is_ssh = (True if 'SSH_TTY' in os.environ else False)
	has_display = (True if 'DISPLAY' in os.environ else False)

	# Make sure the DB opens.
	db = await acp.db.open()

	# Set up Globus.
	# NOTE: This next call consumes `db`, so delete our reference for safety.
	g = await acp.globus.get_client(db)
	del db

	# Check to see if a Globus login is required.
	if acp.globus.needs_login(g) is True:
		print('Globus credentials are either missing or expired.')
		print('A fresh Globus login is required.')

		# Make sure all existing credentials are expired.
		g.logout()

		# If we're not interactive, then we can't continue.
		if not is_interactive:
			print('This requires an interactive session in order to proceed.')
			print('Please re-run this program in an interactive session.')
			sys.exit(1)

		# The ideal thing is to have a web browser for the auth process.
		# That either requires not being in SSH, or being in SSH with X
		# forwarding (in which case we assume there's a local web browser).
		if (not is_ssh) or (is_ssh and has_display):
			print('Press Return to open a web browser and authenticate to Globus.')
			input('')
			try:
				g.login(refresh_tokens=True)
				print('Thank you!')
			except Exception:
				print('An error occurred.  Please try again later.')
				sys.exit(1)

		# In the last case, we'll give the user a URL to visit.
		else:
			try:
				g.login(
					no_local_server = True,
					no_browser = True,
					refresh_tokens = True,
				)
			except Exception:
				print('An error occurred.  Please try again later.')
				sys.exit(1)

	# Say hello
	print('Hello ' + acp.globus.get_name(g))

	# Get our Globus Transfer client
	globus_transfer = acp.globus.get_transfer_client(g)

	# Look up collections, and see which one we want to use.
	collections_list = acp.globus.find_collections(globus_transfer)
	print('')
	if len(collections_list) > 0:
		print('You recently interacted with the following Globus collections:')
		i = 1
		for collection in collections_list:
			print(f"{i}d: {collection.uuid}\n    {collection.name}")
		print('Which AWS S3 collection would you like to use?')

	# Loop until we have a response
	collection: Optional[acp.globus.GlobusCollection] = None
	while collection is None:
		if len(collections_list) > 0:
			response = input('Enter a number or a collection UUID:')
		else:
			response = input('Please enter the UUID of an AWS S3 collection: ')

		# Test for a number and a UUID
		response_is_int = False
		try:
			response_int = int(response)
			debug('Response matches an int')
			response_is_int = True
		except ValueError:
			pass

		response_is_uuid = False
		try:
			response_uuid = uuid.UUID(response)
			debug('Response matches a UUID')
			response_is_uuid = True
		except ValueError:
			pass

		# If a UUID, test that it's a collection.
		if response_is_uuid:
			try:
				collection = acp.globus.get_collection(
					globus_transfer,
					response_uuid,
				)
			except KeyError:
				print(f"Your UUID, {response_uuid}, is not a Globus collection.")

		# If a number, check if it's in range
		if response_is_int:
			# We prompted the user starting at one, so adjust.
			response_int -= 1
			if (response_int < 0) or (response_int >= len(collections_list)):
				print(f"Your selection, {response_int}, was out of range.")
			else:
				# It's in range!  Grab the collection info.
				collection = collections_list[response_int]

	print(f"Using collection \"{collection.name}\"")

# Our actual main!
def main() -> NoReturn:
	asyncio.run(_main())

	# Are we in batch mode?
	if not sys.stdout.isatty():
		print('Sorry, batch mode is not supported yet!')
		sys.exit(1)
	else:
		print('Interactive mode')
		#sys.exit(1)
