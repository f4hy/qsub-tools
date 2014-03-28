#!/usr/bin/env python
import argparse
from tempfile import NamedTemporaryFile
from subprocess import call
import time
import shutil
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
    args = parser.parse_args()


    tmpfile = NamedTemporaryFile()
    tmpfile.write(header.format(NAME=args.name, QUEUE=args.queue))
    if args.wait:
        tmpfile.write("#PBS -W depend=afterok:{}\n".format(":".join(args.wait)))
    tmpfile.write("cd /scratch/PBS_${PBS_JOBID}\n")
    tmpfile.write("echo {}".format(args.command))
    tmpfile.write("\n")
    tmpfile.write(args.command)
    tmpfile.write("\n")
    tmpfile.flush()
    shutil.copyfile(tmpfile.name, "/home/bfahy/last_runscript.txt")
    #call(["cat", tmpfile.name])
    if args.options:
        exelist = ["/opt/pbs/bin/qsub", tmpfile.name]
        exelist[1:1] = ["-l "+ o for o in args.options]
        call(exelist)
    else:
        call(["/opt/pbs/bin/qsub", tmpfile.name])

    time.sleep(2)

if __name__ == "__main__":
    main()
