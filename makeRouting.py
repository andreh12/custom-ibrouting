#!/usr/bin/env python

import sys, os, re

scriptDir = os.path.abspath(os.path.dirname(__file__))


#----------------------------------------------------------------------

def runCmd(cmdParts):

    cmd = " ".join(cmdParts)

    res = os.system(cmd)

    assert res == 0, "failed to run command " + cmd

#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------

if not os.path.exists("rus.txt"):
    runCmd([ "~aholz/oncall-stuff/printRUsInRun.py > rus.txt" ])

if not os.path.exists("bus.txt"):
    runCmd([ "~aholz/oncall-stuff/printBUsInRun.py > bus.txt" ])

if not os.path.exists("iblinkinfo-output"):
    runCmd([ "sudo iblinkinfo > iblinkinfo-output" ])

numRus = len(re.split('\s+',open("rus.txt").read()))
numBus = len(re.split('\s+',open("bus.txt").read()))

cmdParts = [
    os.path.join(scriptDir, "genRoutes.py"),
    "--srcfile rus.txt",
    "--destfile bus.txt",
    "--iblinkfile iblinkinfo-output",
    "--algo " + os.path.join(scriptDir, "ranking03.py")
    ]

runCmd(cmdParts)

import shutil
shutil.move("/tmp/routing-table-%dx%d.txt" % (numRus, numBus),
            "routing-table-%dx%d-algo03.txt" % (numRus, numBus)
            )
