#!/usr/bin/env python

class RoutingTable:
    # a routing table for a switch which can be printed

    #----------------------------------------    

    def __init__(self, linkData, switchLid):

        self.linkData = linkData

        self.switchLid = switchLid

        self.switchData = linkData.getSwitchDataFromLID(switchLid)

        self.lidToOutputPort = {}

        # self.minLid = min(linkData.allLIDs)

        # fix to zero
        self.minLid = 0
        self.maxLid = max(linkData.allLIDs)

        # the first index is zero
        # None means no route defined for this lid,
        # a corresponding line is NOT printed in the output
        self.lidToOutputPort = [ None ] * (self.maxLid + 1)

        #----------
        # find the LIDs which are connected directly here
        # maps from port to peer LID
        #----------
        self.localLIDs = {}
        for line in self.switchData['portData']:

            peerLid = line['peerLid']
            if peerLid == None:
                continue

            port = line['port']
            assert not self.localLIDs.has_key(port)
            self.localLIDs[port] = peerLid

            # set the entry in the local routing table
            self.lidToOutputPort[peerLid] = port

    #----------------------------------------

    def isConnectedToLid(self, lid):
        return lid in self.localLIDs.values()

    #----------------------------------------
    def findLocalPorts(self, lid):
        # returns the ports for a locally connected
        # LID or an empty list of not found
        #
        # note that there can be more than one
        # port to the same peer LID (e.g. leaf
        # to spine switches)

        retval = []
        
        for port, peerLid in self.localLIDs.items():
            if peerLid == lid:
                retval.append(port)

        return retval

    #----------------------------------------

    def addLocalRoute(self, destLid, outputPort):

        # make sure we do not add conflicting routes
        if self.lidToOutputPort[destLid] == None:
            self.lidToOutputPort[destLid] = outputPort
        else:
            # a corresponding entry exists already,
            # make sure it is the same like what is being set now
            assert self.lidToOutputPort[destLid] == outputPort, \
                "trying to assign output port %d for lid %d which already has port %d on switch lid %d" % (
                    outputPort,
                    destLid,
                    self.lidToOutputPort[destLid],
                    self.switchLid
                )

    #----------------------------------------

    def getOutputPortForDestination(self, destLid):
        # returns the output port in the local routing
        # table for the given LID or None
        # if no such route has been defined yet

        return self.lidToOutputPort[destLid]

    #----------------------------------------    

    def doPrint(self, fout):

        # print the header
        #
        # example line:
        #    Unicast lids [0x0-0x1400] of switch DR path slid 0; dlid 0; 0,1,19,32 guid 0xf4521403001d5d40 (MF0;sw-ib-c2f14-14-01:SX6036/U1):
        #
        # the parts after 'DR path' seem to differ slightly from switch to switch but not
        # clear whether this is actually read by OpenSM ?

        print >> fout, "Unicast lids [0x%x-0x%x] of switch DR path slid 0; dlid 0; 0,1,19,32 guid %s (MF0;sw-ib-c2f14-14-01:SX6036/U1):" % (
            self.minLid,
            self.maxLid,
            self.switchData['guid'],
            )

        #----------
        # print the per lid table
        #----------
        print >> fout,"  Lid  Out   Destination"
        print >> fout,"       Port     Info "

        numValidLids = 0
        for lid in range(len(self.lidToOutputPort)):

            outputPort = self.lidToOutputPort[lid]

            if outputPort == None:
                continue
            
            # example line:
            # 0x0001 022 : (Switch portguid 0xf4521403001d56c0: 'MF0;sw-ib-c2f14-44-01:SX6036/U1')

            description = "(no description yet)"

            if self.linkData.isHost(lid):
                hostData = self.linkData.getHostData(lid)

                # example:
                #  (Channel Adapter portguid 0xf452140300f54f51: 'bu-c2d32-20-01 HCA-1')
                description = "(Channel Adapter portguid %s: '%s')" % (
                    hostData['guid'],
                    hostData['fulldesc']
                )

            print >> fout,"0x%04x %03d : %s" % (lid,
                                               outputPort,
                                                description
                                                )

            numValidLids += 1

        print >> fout, "%d valid lids dumped " % numValidLids

    #----------------------------------------
