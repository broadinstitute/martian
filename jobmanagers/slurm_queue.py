#!/usr/bin/env python
#
# Copyright (c) 2020 10x Genomics, Inc. All rights reserved.
#

"""Queries squeue about a list of jobs and parses the output, returning the list
of jobs which are queued, running, or on hold."""

import getpass
import subprocess
import sys


def get_ids():
    """Returns he set of jobids to query from standard input."""
    ids = []
    for jobid in sys.stdin.readlines():
        ids.append(jobid.strip())
    return ids


def mkopts():
    """Gets the command line for squeue.

    Queries all of the current user's jobs rather than filtering with
    `squeue -j <ids>`.  Filtering by job id is unreliable: if even one of
    the requested ids has already been purged from Slurm's job table,
    squeue can return an empty result for the entire query instead of just
    omitting that id, which makes still-queued or still-running jobs
    disappear from the response too.  Querying by user and filtering
    locally avoids that failure mode.
    """
    return ["squeue", "-h", "-o", r"%A %t", "-u", getpass.getuser()]


def execute(cmd):
    """Executes qstat and captures its output."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    if proc.returncode:
        raise OSError(err)
    if not isinstance(out, str):
        out = out.decode()
    if len(out) < 500:
        sys.stderr.write(out)
    else:
        sys.stderr.write(out[:496] + "...")
    return out


def allow_state(state):
    """Returns True if the state code is for a queued or running job."""
    return state in ["CG", "CF", "PD", "R", "RD", "RS", "SI", "SO"]


# Terminal states which should be reported back immediately as an explicit
# failure, rather than just being omitted (which makes Martian wait out the
# generic "job vanished from the queue" grace period before treating it as
# a failure).  Maps the squeue state code to the reason string reported
# upstream.
FAILED_STATES = {
    "NF": "NODE_FAIL",
}


def parse_output(out, ids):
    """Parses the output of squeue.  For jobs which are also in the given set
    of ids of interest, yields (jobid, reason) pairs: reason is None for
    jobs which are still queued or running, or a failure reason string for
    jobs in a state in FAILED_STATES."""
    wanted = set(ids)
    for line in out.split("\n"):
        if not line:
            continue
        line = line.strip()
        if not line:
            continue
        line = line.split(None, 1)
        if len(line) != 2 or line[0] not in wanted:
            continue
        jobid, state = line
        if allow_state(state):
            yield jobid, None
        elif state in FAILED_STATES:
            yield jobid, FAILED_STATES[state]


def main():
    """Reads a set of ids from standard input, queries squeue, and outputs the
    jobids to standard output for jobs which are in the pending state.  Jobs
    which are in a terminal failure state that is otherwise not detectable
    from the queue simply disappearing (e.g. NODE_FAIL) are reported as
    "<jobid> <reason>" so callers can fail them immediately."""
    ids = get_ids()
    if not ids:
        sys.exit(0)
    for jobid, reason in parse_output(execute(mkopts()), ids):
        if reason:
            sys.stdout.write("%s %s\n" % (jobid, reason))
        else:
            sys.stdout.write("%s\n" % jobid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
