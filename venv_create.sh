#/bin/bash
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 noet

# © 2022 The Board of Trustees of the Leland Stanford Junior University

# This script sets up a venv in the project directory.

# Set this to be the specific Python version you want; or, if $PYTHON is
# already defined in the environment, use that.  If the Python executable is in
# your $PATH, then you just need the name; otherwise you might need the
# absolute path.
PYTHON=${PYTHON:-python3.10}

# Exit immediately on command errors
set -e

# Make the venv
echo "Creating venv with Python ${PYTHON}"
$PYTHON -m venv .

# Check if we are using modules.  If yes, then purge the environment.
# (We might have needed a Python module to get the venv working.)
if [ $(declare -F | grep -c module) -gt 0 ]; then
	echo "Unloading any modules."
	module purge
fi

# Everything after this uses the local venv.

# Upgrade pip, and install wheel
echo "Installing/Upgrading pip & wheel"
./bin/python -m pip install --upgrade pip
./bin/python -m pip install wheel

# Run the setup program, in user-editable (or "dev") mode.
echo "Running pip install (editable mode)"
./bin/python -m pip install -e .

# If we're running in a module, warn the user to unload Python
# before continuing.
if [ $(declare -F | grep -c module) -gt 0 ]; then
	echo "WARNING: Before you continue, unload the Python module."
fi
echo "Installation complete!  You may now activate your venv."
