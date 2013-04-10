#!/usr/bin/env python
import argparse
from tempfile import NamedTemporaryFile
from subprocess import call
header="""
#!/bin/sh -f
##########################
#                        #
#   The PBS directives   #
#                        #
##########################

#PBS -N {}
#PBS -l nodes=1:ppn=1
#PBS -o output/output_Yang_Mills_0.$PBS_JOBID
#PBS -e output/error_Yang_Mills_0.$PBS_JOBID
#PBS -j oe
#PBS -l cput=1000:00:00
#PBS -l pcput=100:00:00
#PBS -l walltime=100:00:00
#PBS -q {}
#PBS -m ae
#PBS -M bfahy@andrew.cmu.edu
"""



def main():
    parser = argparse.ArgumentParser(description="Submit a job to do a single command")
    parser.add_argument("command", type=str, help="command to execute")
    parser.add_argument("-n", "--name", type=str, default="testrun", help="set the name of the job")
    parser.add_argument("-q", "--queue", default="red", choices=["green", "blue", "cyan", "magenta", "red"], help="queue to submit to")
    args = parser.parse_args()

    tmpfile = NamedTemporaryFile()
    tmpfile.write(header.format(args.name, args.queue))
    tmpfile.write(args.command)
    call(["qsub", tmpfile.name])


if __name__ == "__main__":
    main()