#!/usr/bin/env python
import argparse
from tempfile import NamedTemporaryFile
from subprocess import call
import time
import shutil
import readinput
import sys
header="""
#!/bin/sh -f
##########################
#                        #
#   The PBS directives   #
#                        #
##########################

#PBS -N {NAME}
#PBS -u bfahy
#PBS -l nodes=1:ppn=1
#PBS -o output_{NAME}_0.$PBS_JOBID
#PBS -e error_{NAME}_0.$PBS_JOBID
#PBS -j oe
#PBS -l cput=1000:00:00
#PBS -l pcput=100:00:00
#PBS -l walltime=100:00:00
#PBS -q {QUEUE}
#PBS -m a
#PBS -M bfahy@andrew.cmu.edu
"""



def main():
    parser = argparse.ArgumentParser(description="Submit a job to do a single command")
    parser.add_argument("command", type=str, help="command to execute")
    parser.add_argument("-n", "--name", type=str, default="singlecommand", help="set the name of the job")
    parser.add_argument("-W", "--wait", type=str, action="append", required=False, help="have job depend upon annother")
    parser.add_argument("-q", "--queue", default="red", choices=["green", "blue", "cyan", "magenta", "red"], help="queue to submit to")
    parser.add_argument("-o", "--options", required=False, action="append", type=str, help="options to pass to qsub")
    parser.add_argument("-a", "--ask", action="store_true", help="ask before submitting")
    parser.add_argument("-d", "--dry_run", action="store_true", help="don't submit, just show what would be'")

    args = parser.parse_args()


    tmpfile = NamedTemporaryFile()
    tmpfile.write(header.format(NAME=args.name, QUEUE=args.queue))
    if args.wait and any(args.wait):
        tmpfile.write("#PBS -W depend=afterok:{}\n".format(":".join([i for i in args.wait if i])))
    tmpfile.write("cd /scratch/PBS_${PBS_JOBID}\n")
    tmpfile.write("echo 'executing: {}'".format(args.command))
    tmpfile.write("\n")
    tmpfile.write(args.command.replace(";", ";\n"))
    tmpfile.write("\n")
    tmpfile.flush()
    shutil.copyfile(tmpfile.name, "/home/bfahy/last_runscript.txt")
    def call_wrap(e):
        if args.dry_run:
            sys.stderr.write("would have ran {} on:".format(repr(e)))
            with open(tmpfile.name, 'r') as f:
                sys.stderr.write(f.read())
            print "FAKEJOBIDNUMBER"
        else:
            if args.ask:
                if readinput.askyesno("execute {} on {} called {}".format(args.command, args.queue, args.name), default=False):
                    call(e)
                    time.sleep(2)
            else:
                call(e)
                time.sleep(2)

    if args.options:
        exelist = ["/opt/pbs/bin/qsub", tmpfile.name]
        exelist[1:1] = ["-l "+ o for o in args.options]
        call_wrap(exelist)
    else:
        call_wrap(["/opt/pbs/bin/qsub", tmpfile.name])

if __name__ == "__main__":
    main()
