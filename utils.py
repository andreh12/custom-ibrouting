#!/usr/bin/env python

import re

#----------------------------------------------------------------------

def findSwitchLIDs(linkData):
    # returns [ leafSwitchLIDs, spineSwitchLIDs ]

    leafSwitchLIDs = []
    spineSwitchLIDs = []

    for lid in linkData.switchLIDs:

        switchData = linkData.getSwitchDataFromLID(lid)

        # check if we have at least one non-switch LID connected
        # (then this a leaf switch)

        isLeafSwitch = False

        for port in switchData['portData']:
            peerLid = port['peerLid']

            if peerLid in linkData.hostLIDs:
                # a host is connected here,
                # so this is a leaf switch
                isLeafSwitch = True
                break

        if isLeafSwitch:
            leafSwitchLIDs.append(lid)
        else:
            spineSwitchLIDs.append(lid)

    return leafSwitchLIDs, spineSwitchLIDs


#----------------------------------------------------------------------

def readHostsFile(fname):
    fin = open(fname)

    retval = []

    for line in fin.read().splitlines():

        # remove comments
        pos = line.find('#')
        if pos != -1:
            line = line[:pos]
        
        line = line.strip()

        if not line:
            # skip empty lines
            # also avoid having a list with a single empty string
            # in the split below
            continue

        # allow for multiple hosts on the same line (to e.g. allow the format
        # produced by ~/oncall-stuff/print{RU,BU}sInRun.py)
        hosts = re.split('\s+', line)

        retval.extend(hosts)

    fin.close()

    return retval

#----------------------------------------------------------------------
