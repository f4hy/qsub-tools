#!/usr/bin/env python
"""
wrapper for queues
"""

import sys
from subprocess import check_output

queues = ("green", "blue", "cyan", "magenta", "red")


def display_usage():

    qstat = check_output("qstat")
    size = max((len(q) for q in queues))

    for q in queues:
        sys.stdout.write("%s has\t\t %d jobs\n" % (q.ljust(size), qstat.count(q)))


def return_first_empty():
    qstat = check_output("qstat")
    for q in queues:
        if qstat.count(q) == 0:
            return q
    return None
