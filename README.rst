S3 Cross-Account Copy post-Globus Transfer
==========================================

This tool exists to work around a problem in Globus' support for `S3
collections <https://docs.globus.org/how-to/access-aws-s3/>`_: It is not
possible to use cross-account access to upload to an AWS S3 bucket.

This tool enables cross-account bucket uploads, in two steps.  In the first
step, you use Globus to upload to a staging bucket that you own.  This tool
monitors the transfer, waiting for it to complete.  Once the transfer is
complete, this tool performs a server-side bucket-to-bucket copy using the S3
API.

The problem
-----------

There are multiple ways to interact with a non-public Amazon S3 bucket that you
(or your AWS account) does not own.  One way is to use a bucket policy, giving
your IAM User permission to interact with the S3 bucket.  This method would
work best with Globus, since Globus only supports IAM User authentication
(without assuming a role).

Although this method would allow cross-account access through Globus, before
Globus interacts with a bucket, it makes a `GetBucketLocation
<>`_ call to determine the bucket's location.  AWS does not allow this call to
be made by anyone other than the bucket's owning AWS account.  Therefore, the
call fails, and Globus reports *Permission Denied*.

How to Install
--------------

This tool is written in Python, and supports Python 3.8+.  It is meant to be
run inside a Python venv, and a Bash script—``venv_create.sh``—is included to
help set up such a venv.

If you don't want to run the script, you can set up the environment by
following these steps:

1. In the clone of this repo, run ``python3.8 -m venv .``.  Replace
   ``python3.8`` with your preferred version, so long as it is at least Python
   3.8.

2. If you used a module (like an Lmod module or a Conda environment) to create
   the venv, unload the module before continuing.  Then, source
   ``./bin/activate`` to enter the venv environment.

3. Upgrade Pip and wheel by running ``python -m pip install --upgrade pip
   wheel``.
    
   .. warning::
   This is important!  This project needs an up-to-date pip in order
   to install properly.

4. Install all dependencies and set up the command by running ``python -m pip
   install -e .``.

How To Use
----------

Once installed, the command ``aws-copy-pt`` will be available in the venv.  Run
the command and follow the prompts.

On first run it will set up a local database to keep track of credentials,
(Globus) collections, (AWS S3) buckets, and transfers.  It will also prompt you
to log in to Globus and give the tool permission to act on your behalf.

In the future, it will be possible to run this command in a batch environment,
so that transfer-monitoring and bucket-to-bucket copies can take place without
an active shell/screen/tmux session.

Copyright & License
-------------------

The contents of this repository are © 2022 The Board of Trustees of the Leland
Stanford Junior University.

Code is made available under the `GNU Affero General Public License, Version 3
<https://www.gnu.org/licenses/agpl-3.0.en.html>`_.  You can read it by clicking
the link or checking out the `LICENSE <blob/main/LICENSE>`_ file.

Documentation is made available under the `GNU Free Documentation License,
Version 1.3 <https://www.gnu.org/licenses/fdl-1.3.html>`_.  You canread it by
clicking the link or checking our the `LICENSE.docs <blob/main/LICENSE.docs>`_
file.
