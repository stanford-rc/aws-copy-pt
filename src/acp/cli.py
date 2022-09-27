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
from typing import NoReturn

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
