#!/usr/bin/env python

import sys

#----------------------------------------------------------------------

class FTStable:
    # corresponds to a routing table on a single device (switch)

    #----------------------------------------

    def __init__(self, guid, description):
        # maps from destination LID to output port
        self.destLidToPort = {}
        self.destLidToDescription = {}

        self.guid = guid
        self.description = description

    #----------------------------------------

    def setPort(self, destLID, outputPort, description):
        self.destLidToPort[destLID] = outputPort
        self.destLidToDescription[destLID] = description

    #----------------------------------------

    def replaceLid(self, oldLid, newLid):
        
        if self.destLidToPort.has_key(newLid):
            raise Exception("new lid " + str(newLid) + " exists already")

        # does NOT insist that the old lid exists
        # and the new one does not
        if self.destLidToPort.has_key(oldLid):

            self.destLidToPort[newLid] = self.destLidToPort[oldLid]
            del self.destLidToPort[oldLid]

        if self.destLidToDescription.has_key(oldLid):
            self.destLidToDescription[newLid] = self.destLidToDescription[oldLid]
            del self.destLidToDescription[oldLid]

    #----------------------------------------

    def removeLid(self, lid):
        # removes all entries corresponding to the given LID
        # 
        # note that the LID may not be known on this LFT
        # (but it actually should)
        if self.destLidToPort.has_key(lid):
            del self.destLidToPort[lid]

        if self.destLidToDescription.has_key(lid):
            del self.destLidToDescription[lid]

    #----------------------------------------
            
    def getOutputPort(self, lid):
        return self.destLidToPort.get(lid, None)

    #----------------------------------------

    def doPrint(self, fout = sys.stdout):
        # print the header
        #
        # example line:
        #    Unicast lids [0x0-0x1400] of switch DR path slid 0; dlid 0; 0,1,19,32 guid 0xf4521403001d5d40 (MF0;sw-ib-c2f14-14-01:SX6036/U1):
        #
        # the parts after 'DR path' seem to differ slightly from switch to switch but not
        # clear whether this is actually read by OpenSM ?

        print >> fout, "Unicast lids [0x%x-0x%x] of switch DR path slid 0; dlid 0; 0,1,19,32 guid %s (%s):" % (
            0, # min(self.destLidToPort.keys()),
            max(self.destLidToPort.keys()),
            self.guid,
            self.description,
            )

        #----------
        # print the per lid table
        #----------
        print >> fout,"  Lid  Out   Destination"
        print >> fout,"       Port     Info "

        numValidLids = 0
        for lid in sorted(self.destLidToPort.keys()):

            outputPort = self.destLidToPort[lid]

            if outputPort == None:
                continue

            description = self.destLidToDescription.get(lid, "no description yet")

            print >> fout,"0x%04x %03d : (%s)" % (lid,
                                               outputPort,
                                                description
                                                )

            numValidLids += 1

        print >> fout, "%d valid lids dumped " % numValidLids

        
#----------------------------------------------------------------------
