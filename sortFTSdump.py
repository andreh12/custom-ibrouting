#!/usr/bin/env python

# sorts the outputs of dump_fts or our own generated routing
# table so that we can better compare them (the order
# in which the switches are dumped may be different, rendering
# a comparison with diff difficult)

import sys, re

# ARGV = sys.argv[1:]
# assert len(ARGV) == 1

switchToLines = {}

# None means no switch header has been seen so far
# an empty list means that a switch header line
# has been seen
currentSwitchLines = None

currentSwitchName = None

def addSwitch():
    if currentSwitchLines != None and len(currentSwitchLines) > 0:
        # flush the old switch
        assert currentSwitchName != None

        assert not switchToLines.has_key(currentSwitchName)

        switchToLines[currentSwitchName] = currentSwitchLines

for line in sys.stdin.read().splitlines():

    # example line:
    #   Unicast lids [0x0-0x1400] of switch DR path slid 0; dlid 0; 0,1,19,32 guid 0xf4521403001d56c0 (MF0;sw-ib-c2f14-44-01:SX6036/U1):

    mo = re.match("Unicast lids \S+ of switch DR path slid \S+; dlid \S+; \S+ guid 0x\S+ \(\S+;(\S+):\S+\):", line)

    if mo:
        # flush the old switch
        addSwitch()

        # clear
        currentSwitchLines = [ line ]
        currentSwitchName = mo.group(1)

        continue

    # just an 'ordinary' line, we must have
    # seen a header line already

    assert currentSwitchLines != None
    
    currentSwitchLines.append(line)

addSwitch()


# now print them in increasing order of switch name

for switchName in sorted(switchToLines.keys()):
    for line in switchToLines[switchName]:
        print line

        
    

    


