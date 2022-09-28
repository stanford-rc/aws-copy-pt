# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

# Globus code!

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

import aiosqlite
import asyncio
import dataclasses
import fair_research_login
import globus_sdk
import json
import sqlite3
from typing import Any
import uuid

import acp.db
from acp.logging import *


# This is the OAuth client ID for our Globus Native App
GLOBUS_CLIENT_ID = 'f584c7eb-818e-4374-9cbb-037456973b9c'

# These are the Globus scopes that we need
REQUIRED_SCOPES = (
	'openid',
	'profile',
	'urn:globus:auth:scope:transfer.api.globus.org:all',
)


# First, make a class to provide for token storage, using our DB
class TokenStorage:

	def __init__(
		self,
		db: sqlite3.Connection,
	) -> None:
		"""Create a new TokenStorage instance.

		:warning: This constructor *consumes* `db`.
		"""
		debug('Creating new Globus TokenStorage')
		self.db = db


	def __del__(self):
		# Close the DB connection.

		# NOTE: This is non-obvious, because the destructor is not
		# asynchronous, but the database handle is.
		# So, we have to reach out, grab the event loop, and add our coroutine
		# to it.
		self.db.close()
	

	def read_tokens(self) -> dict[str, Any]:
		debug('Entering')
		result: dict[str, Any] = dict()

		# Pull all rows from the Globus credentials table
		for row in self.db.execute('SELECT key, json FROM cred_globus'):
			# JSON-decode and add to our result
			result[row[0]] = json.loads(row[1])

		# Return!
		debug(f"Read {len(result)} tokens from storage")
		return result


	def write_tokens(self,
		tokens: dict[str, Any],
	) -> None:
		debug('Entering')
		self.db.execute('BEGIN')
		# Each token is JSON-encoded, and inserted into the DB.
		# If an entry with the same key is already there, that entry is
		# replaced with the new entry.
		debug(f"Writing {len(tokens)} tokens to storage")
		for token in tokens:
			token_json = json.dumps(tokens[token])
			self.db.execute('''
INSERT OR REPLACE INTO cred_globus (key, json) VALUES (?, ?)
				''',
				(token, token_json),
			)
		self.db.commit()
		return


	def clear_tokens(self) -> None:
		debug('Entering')
		self.db.execute('BEGIN')
		self.db.execute('DELETE FROM cred_globus')
		self.db.commit()
		return


@dataclasses.dataclass(
	frozen=True
)
class GlobusCollection:
	uuid: uuid.UUID
	name: str
	server: str


async def get_client(
	db: aiosqlite.Connection,
) -> fair_research_login.NativeClient:
	"""
	"""

	debug('Spawning token storage')
	# NOTE: This is a hack, since Globus stuff is not async.
	token_storage = TokenStorage(
		db = sqlite3.connect(acp.db.db_path()),
	)

	# Since we officially consume db, close it now.
	await db.close()

	# Create and return the client!
	return fair_research_login.NativeClient(
		client_id = GLOBUS_CLIENT_ID,
		app_name = 'AWS S3 Copy post-transfer',
		default_scopes = REQUIRED_SCOPES,
		token_storage = token_storage,
	)


def get_transfer_client(
	client: fair_research_login.NativeClient
) -> globus_sdk.TransferClient:
	"""Return a ready-to-use Globus Transfer client.

	:param client: The native client.

	:returns: A Globus Transfer client.
	"""

	transfer_client = globus_sdk.TransferClient(
		authorizer=client.get_authorizers_by_scope()['urn:globus:auth:scope:transfer.api.globus.org:all']
	)
	return transfer_client


def get_name(
	client: fair_research_login.NativeClient
) -> str:
	"""Return the name of the person who authenticated.

	:param client: The native client.

	:returns: The name (as a 'display name').
	"""

	# We'll need a Globus Auth client for this.
	auth_client = globus_sdk.AuthClient(
		authorizer=client.get_authorizers_by_scope()['openid']
	)

	# Get the userinfo, and return a name
	user_info = auth_client.oauth2_userinfo()
	return user_info['name']


def needs_login(
	client: fair_research_login.NativeClient,
) -> bool:
	"""
	"""
	result = True

	debug('Trying to load tokens')
	try:
		client.load_tokens()

		# Check for all of our scopes
		all_scopes_found = True
		authorizers_by_scope = client.get_authorizers_by_scope()
		for scope in REQUIRED_SCOPES:
			if scope not in authorizers_by_scope:
				all_scopes_found = False

		# If we missed any scopes, then we need login.
		if not all_scopes_found:
			result = True
		else:
			result = False

	# If we had a problem loading/refreshing any tokens, then we need login.
	except fair_research_login.LoadError:
		result = True

	return result


def find_collections(
	client: globus_sdk.TransferClient
) -> list[GlobusCollection]:
	"""Return a list of recently-used collections

	:param client: A Globus Transfer client.

	:returns: A list of Globus Collection UUIDs and names.
	"""
	debug('Searching for recently-used collections')

	endpoints: list[GlobusEndpoint] = list()
	search_results = client.endpoint_search(
		filter_scope='recently-used',
		limit=10,
	)
	for endpoint in search_results:
		endpoints.push(GlobusEndpoint(
			uuid = uuid.UUID(endpoint['id']),
			name = endpoint['display_name'],
			server = endpoint['DATA'][0]['hostname']
		))

	debug(f"Found {len(endpoints)} results")
	return endpoints


def get_collection(
	client: globus_sdk.TransferClient,
	collection_id: uuid.UUID,
) -> GlobusCollection:
	"""Return a Globus Collection name from a UUID.

	This is mainly meant to validate the a UUID is correct.

	:param client: A Globus Transfer client.

	:param collection_id: A Globus Collection UUID.

	:returns: A Globus Collection UUID and name.

	:raise KeyError: The UUID is not a Collection UUID.
	"""
	debug(f"Searching for collection {collection_id}")

	# Use the fulltext search for a UUID
	search_results: Optional[globus_sdk.GlobusHTTPResponse] = None
	try:
		search_results = client.get_endpoint(
			endpoint_id=collection_id,
		)
	except globus_sdk.TransferAPIError:
		pass

	if search_results is not None:
		return GlobusCollection(
			uuid = search_results['id'],
			name = search_results['display_name'],
			server = search_results['DATA'][0]['hostname']
		)
	else:
		raise KeyError(str(collection_id))
