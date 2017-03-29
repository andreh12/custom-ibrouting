#!/usr/bin/env python

import sys, os, re, utils

scriptDir = os.path.abspath(os.path.dirname(__file__))


#----------------------------------------------------------------------

def runCmd(cmdParts):

    cmd = " ".join(cmdParts)

    res = os.system(cmd)

    assert res == 0, "failed to run command " + cmd

#----------------------------------------------------------------------

def makeHostListsFromRun():
    # make the host lists from the RUs and BUs in the current run
    # but only if the files do not exist yet

    if not os.path.exists("rus.txt"):
        runCmd([ "~aholz/oncall-stuff/printRUsInRun.py > rus.txt" ])

    if not os.path.exists("bus.txt"):
        runCmd([ "~aholz/oncall-stuff/printBUsInRun.py > bus.txt" ])





#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
import getpass
username = getpass.getuser()

ARGV = sys.argv[1:]

assert len(ARGV) <= 1, "expected at most one command line argument: algorithm file name (with or without .py)"

if len(ARGV) == 1:
    routingAlgo = ARGV.pop(0)
else:
    if username == 'pzejdl':
        routingAlgo = "RoutingAlgoPetr"
    elif username == 'aholz':
        routingAlgo = 'ranking03'
    else:
        print >> sys.stderr,"don't know the default algorithm for user '%s'" % username
        sys.exit(1)

    print >> sys.stderr,"using routing algorithm",routingAlgo
            

#----------
# check that the corresponding .py file exist
#----------
routingAlgoFile = os.path.join(scriptDir, routingAlgo)
if not routingAlgoFile.endswith(".py"):
    routingAlgoFile += ".py"

if not os.path.exists(routingAlgoFile):
    print >> sys.stderr,"invalid routing algorithm specified, file " + routingAlgoFile + " does not exist"
    sys.exit(1)

#----------


# makeHostListsFromRun()


if not os.path.exists("iblinkinfo-output"):
    runCmd([ "sudo iblinkinfo > iblinkinfo-output" ])

numRus = len(utils.readHostsFile("rus.txt"))
numBus = len(utils.readHostsFile("bus.txt"))


#----------
algoSuffix = os.path.splitext(os.path.basename(routingAlgoFile))[0]

#----------

cmdParts = [
    os.path.join(scriptDir, "genRoutes.py"),
    "--srcfile rus.txt",
    "--destfile bus.txt",
    "--iblinkfile iblinkinfo-output",
    "--algo " + routingAlgoFile,
    "--report routing.html",
    "-o routing-table-%dx%d-%s.txt" % (numRus, numBus, algoSuffix),
    ]

if username == 'pzejdl':
    cmdParts.append("--noplots")

runCmd(cmdParts)

