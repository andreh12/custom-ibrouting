#!/usr/bin/env python

import sys, re

from FTStable import FTStable

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
