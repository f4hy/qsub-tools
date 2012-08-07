#!/usr/bin/env python
"""
Modify pbs script and submit
"""

import sys
import re
import readinput
import os
from subprocess import call

def usage():
    print """Usage:
    sub.py submitscript.sh"""
    exit(1)

def read(filename):
    print sys.argv

    print "reading %s" % filename
    file = open(filename)
    filetext = file.read()
    
    # find #PBS -N gaugeandmeasurerun
    matchname = re.search('#PBS -N (.*)',filetext)
    name = matchname.group(1)
    # find #PBS -l nodes=4:ppn=8
    dimensions = re.search('#PBS -l nodes=(\d+):ppn=(\d+)',filetext)
    nodes = (int)(dimensions.group(1))
    ppn = (int)(dimensions.group(2))

    # find #PBS -q blue
    matchqueue = re.search('#PBS -q (.+)',filetext)
    queue = matchqueue.group(1)

    # find GEOM="1 1 1 8"
    matchgeom = re.search('GEOM="(\d+) (\d+) (\d+) (\d+)"',filetext)
    geom = [int(matchgeom.group(i)) for i in range(1,5)]

    # find PERMDIR="/latticeQCD/raid3/bfahy/develop/gaugeandmeasure/iso"
    matchpermdir = re.search('PERMDIR="(.+)"',filetext)
    permdir = matchpermdir.group(1)

    print "Name %s" % name
    print "Nodes %d, PPN %d" % (nodes,ppn)
    print "Queue %s" %queue
    print geom
    print "permdir %s" % permdir

    return (name,nodes,ppn,queue,geom,permdir)
    

def write(defaults,filename):
    file = open(filename)
    filetext = file.read()
    file.close()

    name,nodes,ppn,queue,geom,permdir=defaults
    
    
    name = readinput.askstring("Set job name",name)

    queue =readinput.askqueue() 

    if queue == "red":
        noderange = 12
        ppn = 32
        sockets = 8
    else:
        noderange = 8
        ppn = 8
        sockets = 2

    sys.stdout.write("select number of nodes (was %d)\n" % nodes)

    #nodes = readinput.selectchoices(list(range(1,noderange+1)),default=nodes,startnum=1)
    nodes = readinput.askrange(1,noderange,nodes)


    if readinput.askyesno("Set permdir to current dir?\n (%s)" %os.getcwd()):
        permdir = os.getcwd()
    else:
        permdir = readinput.askdir("Set perm directory",permdir)


    optimalgeom = [1,1,1,sockets*nodes]

    if readinput.askyesno("use optimal GEOM=%d,%d,%d,%d" % tuple(optimalgeom)):
        geom = optimalgeom
    else:
        geom = readinput.readgeom(geom)

    filetext = re.sub('#PBS -N (.*)','#PBS -N %s'%name,filetext)
    filetext = re.sub('#PBS -l nodes=(\d+):ppn=(\d+)',"#PBS -l nodes=%d:ppn=%d" % (nodes,ppn),filetext)
    filetext = re.sub('#PBS -q (.+)',"#PBS -q %s" %queue,filetext)
    filetext = re.sub('GEOM="(\d+) (\d+) (\d+) (\d+)"','GEOM="%d %d %d %d"' % tuple(geom),filetext)
    filetext = re.sub('PERMDIR="(.+)"','PERMDIR="%s"'%permdir,filetext)

    print filetext

    newfilename = filename + ".tosub"
    print "writing %s" % newfilename

    outfile=open(newfilename,'w')
    outfile.write(filetext)

    if os.uname()[1] == 'erwin':
        if readinput.askyesno("submit %s" % newfilename):
            print "qsubing %s" %newfilename
            call(["qsub",newfilename])

        
    if readinput.askyesno("move %s to %s" %(newfilename,filename),False):
        print "moving %s to %s" % (newfilename,filename)
        call(["mv",newfilename,filename])
        
    
    
    #readinput.selectchoices(['a'])
    
    
    
    
if len(sys.argv) != 2:
    usage()

filename = sys.argv[1]

defaults = read(filename)

write(defaults,filename)

print "done"
