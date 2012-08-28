#!/usr/bin/env python
"""
wrapper for queues
"""

import sys
from subprocess import check_output

queues = ("green", "blue", "cyan", "magenta", "red")

def display_usage():

    qstat = check_output("qstat")

    for q in queues:
        sys.stdout.write("%s has\t\t %d jobs\n" % (q,qstat.count(q)))

def return_first_empty():
    qstat = check_output("qstat")
    for q in queues:
        if q.count(q) == 0:
            return q
            return None
            
    
