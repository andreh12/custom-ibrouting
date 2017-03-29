#!/usr/bin/env python

import sys, gzip, re, os

sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network"))
from iblinkInfoUtils import IBlinkStatusData

# performs some checks on the output of dumpfts

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

class MultiFTStable:
    # corresponds to the contents of an FTS file (i.e. multiple
    # LFT tables)

    def __init__(self, fin):
        # fin must be a file like object
        
        # first index is switch lid or guid (as long as the lid is not known)
        # value is a FTStable object
        self.routingTables = {}

        self.guidToLID = {}
        self.guidToDescription = {}

        # guids of the switches, in order in which they were read
        self.switchGUIDorder = []

        #----------

        for line in fin.read().splitlines():
            # example:
            #   Unicast lids [0x0-0x1400] of switch DR path slid 0; dlid 0; 0,1,19,32 guid 0xf4521403001d5d40 (MF0;sw-ib-c2f14-14-01:SX6036/U1):

            mo = re.match('Unicast lids \[\S+\] of switch DR path slid \d+; dlid \d+; \S+ guid (0x[0-9a-f]+) \((\S+)\):$', line)
            if mo:
                # use GUID at the moment
                switchGUID = mo.group(1)
                switchName = mo.group(2)

                self.switchGUIDorder.append(switchGUID)

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

            if not self.routingTables.has_key(switchGUID):
                self.routingTables[switchGUID] = FTStable(switchGUID, switchName)

            #----------

            # try to see if we can associate LID to a GUID

            mo = re.match("Switch portguid (0x[0-9a-f]+): '(.*)'", description)
            guid = None
            if mo:
                guid = mo.group(1)
                description2 = mo.group(2)

            else:
                mo = re.match("Channel Adapter portguid (0x[0-9a-f]+): '(.*)'", description)
                if mo:
                    guid = mo.group(1)
                    description2 = mo.group(2)
                else:
                    description2 = None

            self.routingTables[switchGUID].setPort(destLid,outputPort, description)

            if guid == None:
                print "warning: unexpected description format '%s'" % description
            else:
                self.addGUID(guid, destLid, description2)


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
    def addGUID(self, guid, lid, description):
        # description is things like 'ibmon-c2e15-43-01 HCA-1'

        if self.guidToLID.has_key(guid):
            assert self.guidToLID[guid] == lid
        else:
            self.guidToLID[guid] = lid
            self.guidToDescription[guid] = description

    #----------------------------------------

    def getAllLids(self):

        return sorted(self.guidToLID.values())

    #----------------------------------------

    def getLIDfromGUID(self, guid):
        # @return None if not found

        return self.guidToLID.get(guid, None)

    #----------------------------------------

    def getGUIDfromLID(self, lid):
        # @return None if not found
        
        # actually just returns the first hit,
        # does not check for duplicates

        for guid, theLid in self.guidToLID.items():
            if lid == theLid:
                return guid

        # not found
        return None

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

            for lid, port in switchTable.destLidToPort.items():
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
    
    #----------------------------------------

    def replaceLid(self, oldLid, newLid):
        # replaces a lid by a new lid. Throws an exception
        # if the new lid already exists or the old one does not

        if not oldLid in self.guidToLID.values():
            raise Exception("old lid " + str(oldLid) + " not found")

        if newLid in self.guidToLID.values():
            raise Exception("new lid " + str(newLid) + " exists already")

        #----------
        # self.routingTables
        #----------
        for routingTable in self.routingTables.values():
            routingTable.replaceLid(oldLid, newLid)

        # if this is a switch, replace it
        if self.routingTables.has_key(oldLid):
            assert not self.routingTables.has_key(newLid), "internal error"
            
            self.routingTables[newLid] = self.routingTables[oldLid]
            del self.routingTables[oldLid]

        #----------
        # self.guidToLID
        #----------        

        guid = self.getGUIDfromLID(oldLid)
        
        assert self.getGUIDfromLID(newLid) == None, "internal error"

        self.guidToLID[guid] = newLid

        #----------
        # self.switchLids
        #----------

        assert not newLid in self.switchLids
        if oldLid in self.switchLids:
            # it's a switch 
            self.switchLids.remove(oldLid)
            self.switchLids.add(newLid)

    #----------------------------------------

    def removeLid(self, lid):
        # removes all entries corresponding to the given LID
        #
        # refuses to remove LIDs of switches (in principle
        # this would remove the entire switch)
        if not lid in self.guidToLID.values():
            raise Exception("lid " + str(lid) + " not found")

        # check whether this is a switch
        if self.routingTables.has_key(lid):
            raise Exception("lid " + str(lid) + " corresponds to a switch, refusing to remove it")
        #----------
        # self.routingTables
        #----------
        for routingTable in self.routingTables.values():
            routingTable.removeLid(lid)

        #----------
        # self.guidToLID
        #----------        

        guid = self.getGUIDfromLID(lid)
        del self.guidToLID[guid]

    #----------------------------------------

    def doPrint(self, fout = sys.stdout):

        # print switches in same order as they were read
        for guid in self.switchGUIDorder:
            lid = self.guidToLID[guid]

            routingTable = self.routingTables[lid]
            routingTable.doPrint(fout)


#----------------------------------------------------------------------

def checkMissingEntries(ftsTable, linkData):
    # look for missing entries, i.e. check if all routing tables have entries for all LIDs

    allLIDs = sorted(linkData.allLIDs)

    pcLids = ftsTable.getPcLids()

    for switchLid, switchTable in ftsTable.routingTables.items():
        # for lid in ftsTable.getAllLids():
        for lid in allLIDs:
            if not switchTable.destLidToPort.has_key(lid):
                if lid in pcLids:
                    typeName = "pc"
                elif lid in ftsTable.switchLids:
                    typeName = 'switch'
                else:
                    assert False

                print "switch %d does not have an entry for %s lid %d" % (switchLid, typeName, lid)


#----------------------------------------------------------------------

def checkConnectivity(ftsTable, linkData):
    # check that from each lid we can reach each other lid

    maxPathLength = 10

    allLids = ftsTable.getAllLids()

    pcLids = ftsTable.getPcLids()

    for srcLid in sorted(allLids):
        # for the moment, do not test switch to switch connections
        # if srcLid in ftsTable.switchLids:
        #    continue


        # if the source is a PC, we first go to the switch
        if srcLid in pcLids:
            switchPortData = ftsTable.getSwitchPortFromPClid(srcLid)

            # go to the switch
            currentSwitchLid = switchPortData['switchLid']

        else:
            # we start from a switch
            currentSwitchLid = srcLid
            

        for destLid in allLids:
            ## if destLid in ftsTable.switchLids:
            ##     # skip test for reaching switches
            ##     continue


            switchLidsSeen = [ ]

            pathLength = 0

            while pathLength < maxPathLength:

                # get the routing table of the switch
                routingTable = ftsTable.routingTables[currentSwitchLid]

                switchLidsSeen.append(currentSwitchLid)

                # check if the destination is connected to this switch
                if ftsTable.getSwitchPortFromPClid(destLid)['switchLid'] == currentSwitchLid:
                    # yes, we've found the destination
                    # TODO: check again that it points to the 
                    #       right output port
                    break

                if currentSwitchLid == destLid:
                    # we've found a destination switch
                    break

                # we must go over another switch
                # we must know which switch LID is connected to the output port
                # to get the next routing table
                # 
                # however we can't know what is at the other end
                # of the cable without iblinkinfo data
                outputPort = routingTable.getOutputPort(destLid)

                peerSwitchData = linkData.getSwitchPortData(currentSwitchLid, outputPort)

                peerLid = peerSwitchData['peerLid']

                # prepare next iteration
                currentSwitchLid = peerLid

                pathLength += 1

                

            if pathLength >= maxPathLength:
                print "loop detected from %d to %d" % (srcLid, destLid),switchLidsSeen
            else:
                print "ok from %d to %d" % (srcLid, destLid),switchLidsSeen
            



#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------

if __name__ == '__main__':

    ARGV = sys.argv[1:]

    assert len(ARGV) == 2

    fname = ARGV.pop(0)

    if fname.endswith(".gz"):
        fin = gzip.open(fname)
    else:
        fin = open(fname)


    ftsTable = MultiFTStable(fin)


    #----------
    iblinkStatusfile = ARGV.pop(0)

    linkData = IBlinkStatusData.fromIBlinkInfoOutput(open(iblinkStatusfile).read())

    #----------
    # perform checks
    #----------

    checkMissingEntries(ftsTable, linkData)

    # check that we can reach lid from each other lid
    checkConnectivity(ftsTable, linkData)


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


