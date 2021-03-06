#!/usr/bin/env python
"""
Modify pbs script and submit
"""

import sys
import re
import readinput
import os
import qstat
import argparse
from subprocess import call
from fractions import gcd


# noderange,ppn,sockets,cput
red_settings = (12, 32, 8, 5000)
other_settings = (8, 8, 2, 1000)

WARNING = '\033[93m'
ENDC = '\033[0m'


filetext = None


def main():
    parser = argparse.ArgumentParser(description="Walk through submitting a script with qsub first setting up variables")
    parser.add_argument("filename", type=str, help="submit script to edit/submit")
    parser.add_argument("-n", "--name", type=str, help="set the name of the job")
    parser.add_argument("-c", "--count", type=int, help="number of nodes to run on")
    parser.add_argument("-q", "--queue", choices=["green", "blue", "cyan", "magenta", "red"], help="queue to submit to")
    parser.add_argument("-g", "--geom", type=str, help="geom must be in form '1,1,1,1'")
    parser.add_argument("-a", "--auto", action="store_true", help="automatically select defaults")
    parser.add_argument("-d", "--dry", action="store_true", help="dry run, don't submit'")
    args = parser.parse_args()

    try:
        if args.geom and map(type,[int(i) for i in args.geom.split(",")]) != map(type,[1, 2, 3, 4]):
            raise ValueError
        else:
            print "valid geom"
    except Exception as e:
        print "Invalid geom"
        print e
        exit(1)

    filename = args.filename
    readfiletext(filename)
    name = readname()
    nodes, ppn = readnodes()
    queue = readqueue()
    geom = readgeom()
    layout = readlayout()
    permdir = readpermdir()
    cput = readcput()
    print "Name %s" % name
    print "Nodes %d, PPN %d" % (nodes, ppn)
    print "Queue %s" % queue
    print "cput hours %s" % cput
    print "permdir %s" % permdir
    if geom:
        print "geom", geom
        if layout:
            print "layout %s" % layout

    if (args.name):
        print "set name to {}".format(args.name)
        name = args.name
    elif not args.auto:         # auto just use the old name as the deafult
        name = readinput.askstring("Set job name", name)

    if (args.queue):
        print "set queue to {}".format(args.name)
        queue = args.queue
    else:
        queue = setqueue(queue,auto=args.auto)

    permdir = setpermdir(auto=args.auto)

    serial = (geom is None)

    if args.count:
        nodes = args.count

    if serial:
        print "setting serial settings"
        nodes, ppn, sockets, cput = setserialsettings(queue)
    else:
        print "setting parallel settings"
        nodes, ppn, sockets, cput = setparallelsettings(queue, nodes, auto=args.auto)
        if args.geom:
            geom = (int(i) for i in args.geom.split(","))
        else:
            geom = setgeom(nodes, ppn, layout, geom, auto=args.auto)

    newtext = makereplacements(name, nodes, ppn, queue, geom, permdir, cput)
    newfilename = filename + ".tosub"
    print "writing %s" % newfilename

    with open(newfilename, 'w') as outfile:
        outfile.write(newtext)

    if os.uname()[1] == 'erwin':
        if (args.auto and not args.dry) or readinput.askyesno("submit %s" % newfilename):
            print "qsubing %s" % newfilename
            call(["qsub", newfilename])

    if args.auto or readinput.askyesno("move %s to %s" % (newfilename, filename)):
        print "moving %s to %s" % (newfilename, filename)
        call(["mv", newfilename, filename])

    print "done"


def setqueue(queue, auto=False):
    if os.uname()[1] == 'erwin':
        qstat.display_usage()
        # IF we are on a non red queue currently, find the best one
        if queue != "red":
            oldqueue = queue
            queue = qstat.return_first_empty()
            print "empty queue is %s" % queue
            if queue is None:
                queue = oldqueue

    if auto:
        return queue
    else:
        return readinput.askqueue(queue)


def setserialsettings(queue):
    if queue == "red":
        noderange, ppn, sockets, cput = red_settings
    else:
        noderange, ppn, sockets, cput = other_settings
    nodes = 1
    ppn = 1
    return (nodes, ppn, sockets, cput)


def setparallelsettings(queue, previousnodes, auto=False):
    if queue == "red":
        noderange, ppn, sockets, cput = red_settings
    else:
        noderange, ppn, sockets, cput = other_settings
    sys.stdout.write("select number of nodes (was %d)\n" % previousnodes)

    #nodes = readinput.selectchoices(list(range(1,noderange+1)),default=nodes,startnum=1)
    if auto:
        return (previousnodes, ppn, sockets, cput)
    nodes = readinput.askrange(1, noderange, previousnodes)
    return (nodes, ppn, sockets, cput)


def setpermdir(auto=False):
    if auto:
        permdir = os.getcwd()
        return permdir
    if readinput.askyesno("Set permdir to current dir?\n (%s)" % os.getcwd()):
        permdir = os.getcwd()
    else:
        permdir = readinput.askdir("Set perm directory", permdir)
    return permdir


def findoptimalgeom(nodes, ppn, layout):
    cores = ppn * nodes

    coresleft = cores
    optimalgeom = []
    for latticesize in reversed(layout):
        print latticesize
        optimal = gcd(coresleft, latticesize)  # put at the begining
        optimalgeom.insert(0, optimal)
        coresleft = coresleft / optimal

    if coresleft != 1:
        print WARNING + "unable to find optimal geom" + ENDC
        optimalgeom = None

    return optimalgeom


def setgeom(nodes, ppn, layout, geom, auto=False):
    if layout is not None:
        optgeom = findoptimalgeom(nodes, ppn, layout)
    else:
        print WARNING + "No layout set, so optimal geom not checked!" + ENDC
        optgeom = None

    if auto:
        if optgeom:
            return optgeom
        else:
            return geom

    if optgeom and readinput.askyesno("use optimal GEOM=%d,%d,%d,%d" % tuple(optgeom)):
        geom = optgeom
    elif readinput.askyesno("use previous GEOM=%d,%d,%d,%d" % tuple(geom)):
        pass
    else:
        geom = readinput.readgeom(geom)
    return geom


def makereplacements(name, nodes, ppn, queue, geom, permdir, cput):
    newtext = filetext
    newtext = re.sub('#PBS -N (.*)', '#PBS -N %s' % name, newtext)

    node_search_text = '#PBS -l nodes=(\d+):ppn=(\d+)'
    node_replace_text = "#PBS -l nodes=%d:ppn=%d" % (nodes, ppn)
    newtext = re.sub(node_search_text, node_replace_text, newtext)

    newtext = re.sub('#PBS -q (.+)', "#PBS -q %s" % queue, newtext)

    if geom is not None:
        geom_search_text = 'GEOM="(\d+) (\d+) (\d+) (\d+)"'
        geom_replace_text = 'GEOM="%d %d %d %d"' % tuple(geom)
        newtext = re.sub(geom_search_text, geom_replace_text, newtext)

    newtext = re.sub('PERMDIR="(.+)"', 'PERMDIR="%s"' % permdir, newtext)
    newtext = re.sub('#PBS -l *cput=(\d+)', '#PBS -l cput=%s' % cput, newtext)
    return newtext


def readfiletext(filename):
    print "reading %s" % filename
    global filetext
    with open(filename) as readfile:
        filetext = readfile.read()


def readnodes():
    # find #PBS -l nodes=4:ppn=8
    dimensions = re.search('#PBS -l nodes=(\d+):ppn=(\d+)', filetext)
    nodes = (int)(dimensions.group(1))
    ppn = (int)(dimensions.group(2))
    return (nodes, ppn)


def readqueue():
    # find #PBS -q blue
    matchqueue = re.search('#PBS -q (.+)', filetext)
    queue = matchqueue.group(1)
    return queue


def readgeom():
    # find GEOM="1 1 1 8"
    matchgeom = re.search('GEOM="(\d+) (\d+) (\d+) (\d+)"', filetext)
    try:
        geom = [int(matchgeom.group(i)) for i in range(1, 5)]
    except AttributeError:
        print WARNING + "WARNING: Geom not found" + ENDC
        geom = None
    return geom


def readlayout():
    #find CHROMAINPUTFILE="gaugeandmeasuretest.xml"
    matchxmlfilename = re.search('CHROMAINPUTFILE="(.+)"', filetext)
    layout = None
    try:
        xmlfilename = matchxmlfilename.group(1)
    except AttributeError:
        print WARNING + "WARNING: xmlconfig file not found" + ENDC
        xmlfilename = None

    if xmlfilename:
        try:
            xmlfile = open(xmlfilename)
            xmlfiletext = xmlfile.read()
            # match         <nrow>16 16 16 36</nrow>
            matchlayout = re.search('<nrow>(\d+) (\d+) (\d+) (\d+)</nrow>', xmlfiletext)
            layout = [int(matchlayout.group(i)) for i in range(1, 5)]
            print layout
        except IOError:
            print WARNING + "Error! {} file not found".format(xmlfilename) + ENDC
            exit(0)
        except AttributeError:
            print WARNING + "WARNING: no chroma config file" + ENDC
            layout = None
    return layout


def readname():
    # find #PBS -N gaugeandmeasurerun
    matchname = re.search('#PBS -N (.*)', filetext)
    name = matchname.group(1)
    return name


def readpermdir():
    # find PERMDIR="/latticeQCD/raid3/bfahy/develop/gaugeandmeasure/iso"
    matchpermdir = re.search('PERMDIR="(.+)"', filetext)
    permdir = matchpermdir.group(1)
    return permdir


def readcput():
    # find #PBS -l cput=1000:00:00
    matchcput = re.search('#PBS -l *cput=(\d+)', filetext)
    cput = matchcput.group(1)
    return cput

if __name__ == "__main__":
    main()
