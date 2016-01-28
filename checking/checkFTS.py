#!/usr/bin/env python

import sys, gzip, re

# performs some checks on the output of dumpfts

#----------------------------------------------------------------------

class MultiFTStable:
    # corresponds to the contents of an FTS file (i.e. multiple
    # LFT tables)

    def __init__(self, fin):
        # fin must be a file like object
        
        # first index is switch lid or guid (as long as the lid is not known)
        # second index is destination lid
        # value is switch output port
        self.routingTables = {}

        self.guidToLID = {}

        #----------

        for line in fin.read().splitlines():
            # example:
            #   Unicast lids [0x0-0x1400] of switch DR path slid 0; dlid 0; 0,1,19,32 guid 0xf4521403001d5d40 (MF0;sw-ib-c2f14-14-01:SX6036/U1):

            mo = re.match('Unicast lids \[\S+\] of switch DR path slid \d+; dlid \d+; \S+ guid (0x[0-9a-f]+) \((\S+)\):$', line)
            if mo:
                # use GUID at the moment
                switchGUID = mo.group(1)
                switchName = mo.group(2)

                continue


            if re.match("\s*Lid\s+Out\s+Destination", line):
                continue

            if re.match("\s*Port\s+Info", line):
                continue

            if re.match("\d+ valid lids dumped", line):
                continue

            # assume it's a regular port entry
            # e.g.
            #   0x0003 024 : (Switch portguid 0xf4521403001d5340: 'MF0;sw-ib-c2f15-27-01:SX6036/U1')
            mo = re.match("(0x[0-9a-f]{4}) (\d\d\d) : \((.*)\)\s*$", line)
            assert mo

            destLid = int(mo.group(1), 16)
            outputPort = int(mo.group(2))
            description = mo.group(3)

            self.routingTables.setdefault(switchGUID, {})[destLid] = outputPort

            # try to see if we can associate LID to a GUID

            mo = re.match("Switch portguid (0x[0-9a-f]+):", description)
            guid = None
            if mo:
                guid = mo.group(1)

            else:
                mo = re.match("Channel Adapter portguid (0x[0-9a-f]+):", description)
                if mo:
                    guid = mo.group(1)

            if guid == None:
                print "warning: unexpected description format '%s'" % description
            else:
                self.addGUID(guid, destLid)


        # replace switch GUIDs by LIDs
        switchGUIDs = self.routingTables.keys()

        self.switchLids = set()
        for switchGUID in switchGUIDs:
            lid = self.guidToLID[switchGUID]

            self.switchLids.add(lid)

            self.routingTables[lid] = self.routingTables[switchGUID]
            del self.routingTables[switchGUID]

        self.__fillPClidToSwitchPort()

    #----------------------------------------
    def addGUID(self, guid, lid):

        if self.guidToLID.has_key(guid):
            assert self.guidToLID[guid] == lid
        else:
            self.guidToLID[guid] = lid

    #----------------------------------------

    def getAllLids(self):

        return sorted(self.guidToLID.values())

    #----------------------------------------

    def getPcLids(self):
        return set(self.getAllLids()) - self.switchLids

    #----------------------------------------

    def __fillPClidToSwitchPort(self):
        # index is PC LID, value is a dict of switchLid and switchPort
        self.pcLidToSwitchPort = {}
        for switchLid, switchTable in self.routingTables.items():

            portCounts = {}

            # reverse map
            portToLid = {}

            for lid, port in switchTable.items():
                portCounts[port] = portCounts.get(port,0) + 1

                portToLid[port] = lid

            # now look at those ports for which exactly one LID was in the table
            # (we assume that the routing table is correct here... maybe we should
            # not do this !)
            for port, count in portCounts.items():
                if count > 1:
                    # a switch is connected here
                    # TODO: this will fail if we have more than one LID per PC
                    #
                    # how do we know which switch is connected here ?
                    pass

                if count == 1:
                    lid = portToLid[port]

                    assert not self.pcLidToSwitchPort.has_key(lid)

                    self.pcLidToSwitchPort[lid] = dict(switchLid = switchLid,
                                                       switchPort = port)
        

    #----------------------------------------

    def getSwitchPortFromPClid(self, pclid):
        # returns a dict with 'switchLid' and 'switchPort'

        return self.pcLidToSwitchPort[pclid]
    

#----------------------------------------------------------------------

def checkMissingEntries(ftsTable):
    # look for missing entries, i.e. check if all routing tables have entries for all LIDs
    for switchLid, switchTable in ftsTable.routingTables.items():
        for lid in ftsTable.getAllLids():
            if not switchTable.has_key(lid):
                if lid in pcLids:
                    typeName = "pc"
                elif lid in ftsTable.switchLids:
                    typeName = 'switch'
                else:
                    assert False

                print "switch %d does not have an entry for %s lid %d" % (switchLid, typeName, lid)


#----------------------------------------------------------------------

def checkConnectivity(ftsTable):
    # check that from each lid we can reach each other lid

    maxPathLength = 10

    allLids = ftsTable.getAllLids()

    pcLids = ftsTable.getPcLids()

    for srcLid in allLids:
        # for the moment, do not test switch to switch connections
        if srcLid in ftsTable.switchLids:
            continue


        # if the source is a PC, we first go to the switch
        if srcLid in pcLids:
            switchPort = ftsTable.getSwitchPortFromPClid(srcLid)

            # go to the switch
            srcLid = switchPort['switchLid']

        # get the routing table of the switch
        routingTable = ftsTable.routingTables[srcLid]
        currentSwitchLid = srcLid

        for destLid in allLids:
            if destLid in ftsTable.switchLids:
                # skip test for reaching switches
                continue

            pathLength = 0

            while pathLength < maxPathLength:

                # check if the destination is connected to this switch
                if ftsTable.getSwitchPortFromPClid(destLid)['switchLid'] == currentSwitchLid:
                    # yes, we've found the destination
                    # TODO: check again that it points to the 
                    #       right output port
                    break

                # we must go over another switch
                # we must know which switch LID is connected to the output port
                # to get the next routing table
                outputPort = routingTable[destLid]
                

                # prepare next iteration
                pathLength += 1

                

            if pathLength >= maxPathLength:
                print "loop detected from %d to %d" % (srcLid, destLid)
            else:
                print "ok from %d to %d" % (srcLid, destLid)
            



#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------

ARGV = sys.argv[1:]

assert len(ARGV) == 1

fname = ARGV.pop(0)

if fname.endswith(".gz"):
    fin = gzip.open(fname)
else:
    fin = open(fname)


ftsTable = MultiFTStable(fin)


#----------
# perform checks
#----------

# checkMissingEntries(ftsTable)

# check that we can reach lid from each other lid
checkConnectivity(ftsTable)


if False:
    #----------
    # find ports where switches are connected to switches
    #
    # assume ports for which there is more than one destination LID
    # are connected to another switch and those on which
    # only one destination LID is found are PCs (this may actually
    # also happen for a switch which has only one port connected...)
    #----------
    pass

#----------
# find to which switch each PC is connected to: look at 
# those switch ports to which only one destination LID
# is assigned
#----------


