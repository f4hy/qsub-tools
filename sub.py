#!/usr/bin/env python
"""
Modify pbs script and submit
"""

import sys
import re
import readinput
import os
import qstat
from subprocess import call
from fractions import gcd

# noderange,ppn,sockets,cput
red_settings = (12, 32, 8, 5000)
other_settings = (8, 8, 2, 1000)


def usage():
    print """Usage:
    sub.py submitscript.sh"""
    exit(1)


def read(filename):
    print sys.argv

    print "reading %s" % filename
    readfile = open(filename)
    filetext = readfile.read()
    readfile.close()
    
    # find #PBS -N gaugeandmeasurerun
    matchname = re.search('#PBS -N (.*)', filetext)
    name = matchname.group(1)
    # find #PBS -l nodes=4:ppn=8
    dimensions = re.search('#PBS -l nodes=(\d+):ppn=(\d+)', filetext)
    nodes = (int)(dimensions.group(1))
    ppn = (int)(dimensions.group(2))

    # find #PBS -q blue
    matchqueue = re.search('#PBS -q (.+)', filetext)
    queue = matchqueue.group(1)

    # find GEOM="1 1 1 8"
    matchgeom = re.search('GEOM="(\d+) (\d+) (\d+) (\d+)"', filetext)
    try:
        geom = [int(matchgeom.group(i)) for i in range(1, 5)]
    except AttributeError:
        print "WARNING: Geom not found"
        geom = None


    # find PERMDIR="/latticeQCD/raid3/bfahy/develop/gaugeandmeasure/iso"
    matchpermdir = re.search('PERMDIR="(.+)"', filetext)
    permdir = matchpermdir.group(1)

    # find #PBS -l cput=1000:00:00
    matchcput = re.search('#PBS -l *cput=(\d+)', filetext)
    cput = matchcput.group(1)

    if geom is None:
        layout = None
    else:
        #find CHROMAINPUTFILE="gaugeandmeasuretest.xml"
        matchxmlfilename = re.search('CHROMAINPUTFILE="(.+)"', filetext)
        xmlfilename = matchxmlfilename.group(1)

        if xmlfilename:
            try:
                xmlfile = open(xmlfilename)
                xmlfiletext = xmlfile.read()
                # match         <nrow>16 16 16 36</nrow>
                matchlayout = re.search('<nrow>(\d+) (\d+) (\d+) (\d+)</nrow>',xmlfiletext)
                layout = [int(matchlayout.group(i)) for i in range(1, 5)]
            except IOError:
                print "Error! {} file not found".format(xmlfilename)
                exit(0)
            except AttributeError:
                print "WARNING: no chroma config file"
                layout = None

    print "Name %s" % name
    print "Nodes %d, PPN %d" % (nodes, ppn)
    print "Queue %s" % queue
    print "cput hours %s" % cput
    print geom
    print "permdir %s" % permdir
    print "layout %s" % layout


    return (name, nodes, ppn, queue, geom, permdir, cput, layout)



def factors(n):
    return [i for i in range(1, n//2 + 1) if not n%i] + [n]

def write(defaults, filename):
    writefile = open(filename)
    filetext = writefile.read()
    writefile.close()

    name, nodes, ppn, queue, geom, permdir, cput, layout = defaults

    name = readinput.askstring("Set job name", name)


    if os.uname()[1] == 'erwin':
        qstat.display_usage()
        # IF we are on a non red queue currently, find the best one
        if queue != "red":
            oldqueue = queue
            queue = qstat.return_first_empty()
            print "empty queue is %s" % queue
            if queue == None:
                queue = oldqueue

        
    queue = readinput.askqueue(queue)

    if queue == "red":
        noderange, ppn, sockets, cput = red_settings
    else:
        noderange, ppn, sockets, cput = other_settings

    sys.stdout.write("select number of nodes (was %d)\n" % nodes)

    #nodes = readinput.selectchoices(list(range(1,noderange+1)),default=nodes,startnum=1)
    nodes = readinput.askrange(1, noderange, nodes)

    if readinput.askyesno("Set permdir to current dir?\n (%s)" % os.getcwd()):
        permdir = os.getcwd()
    else:
        permdir = readinput.askdir("Set perm directory", permdir)

    if geom is not None:
        cores = ppn*nodes

        coresleft = cores
        optimalgeom = []
        for latticesize in reversed(layout):
            print latticesize
            optimal = gcd(coresleft,latticesize) # put at the begining
            optimalgeom.insert(0,optimal)
            coresleft = coresleft / optimal

        if coresleft != 1:
            print "unable to find optimal geom"
            optimalgeom = None

        if optimalgeom and readinput.askyesno("use optimal GEOM=%d,%d,%d,%d" % tuple(optimalgeom)):
            geom = optimalgeom
        elif readinput.askyesno("use previous GEOM=%d,%d,%d,%d" % tuple(geom)):
            pass
        else:
            geom = readinput.readgeom(geom)

    filetext = re.sub('#PBS -N (.*)', '#PBS -N %s' % name, filetext)

    node_search_text = '#PBS -l nodes=(\d+):ppn=(\d+)'
    node_replace_text = "#PBS -l nodes=%d:ppn=%d" % (nodes, ppn)
    filetext = re.sub(node_search_text, node_replace_text, filetext)

    filetext = re.sub('#PBS -q (.+)', "#PBS -q %s" % queue, filetext)

    if geom is not None:
        geom_search_text = 'GEOM="(\d+) (\d+) (\d+) (\d+)"'
        geom_replace_text = 'GEOM="%d %d %d %d"' % tuple(geom)
        filetext = re.sub(geom_search_text, geom_replace_text, filetext)

    filetext = re.sub('PERMDIR="(.+)"', 'PERMDIR="%s"' % permdir, filetext)
    filetext = re.sub('#PBS -l *cput=(\d+)', '#PBS -l cput=%s'% cput , filetext)

    print filetext

    newfilename = filename + ".tosub"
    print "writing %s" % newfilename

    with open(newfilename, 'w') as outfile:
        outfile.write(filetext)

    if os.uname()[1] == 'erwin':
        if readinput.askyesno("submit %s" % newfilename):
            print "qsubing %s" % newfilename
            call(["qsub", newfilename])

    if readinput.askyesno("move %s to %s" % (newfilename, filename)):
        print "moving %s to %s" % (newfilename, filename)
        call(["mv", newfilename, filename])

if len(sys.argv) != 2:
    usage()

script_filename = sys.argv[1]

read_defaults = read(script_filename)

write(read_defaults, script_filename)

print "done"
