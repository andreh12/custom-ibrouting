#!/usr/bin/env python

import sys

from FabricTable import FabricTable
from OccupancyTable import OccupancyTable
import utils

from Route import Route

class SwitchToSwitchTable:
    # Contains leaf to spine and spine to leaf connection tables with port numbers
    # Contains method for getting swith to switch connections in round-robin way
    
    #----------------------------------------
    
    def __init__(self, leafSwitchLIDs, spineSwitchLIDs, fabricTable):

        self.leafSwitchLIDs = leafSwitchLIDs
        self.spineSwitchLIDs = spineSwitchLIDs
        self.fabricTable = fabricTable
        
        print "*   Filling leaf to spine port table"
        
        # leaf to spine switch table with port numbers
        self.leafToSpine = {}
        
        for leafLid in self.leafSwitchLIDs:
            spineDict = {}
            self.leafToSpine[leafLid] = spineDict
            
            for spineLid in self.spineSwitchLIDs:
                record = {}
                record["index"] = 0
                record["ports"] = self.fabricTable.findLocalPortsForDestination(leafLid, spineLid)
                
                spineDict[spineLid] = record
                
        self.leafToSpine[leafLid] = spineDict


        print "*   Filling spine to leaf port table"
        # spine to leaf switch table with port numbers
        self.spineToLeaf = {}
        
        for spineLid in self.spineSwitchLIDs:
            leafDict = {}
            self.spineToLeaf[leafLid] = leafDict
                        
            for leafLid in self.leafSwitchLIDs:
                record = {}
                record["index"] = 0
                record["ports"] = self.fabricTable.findLocalPortsForDestination(spineLid, leafLid)
                                
                leafDict[leafLid] = record
                
            self.spineToLeaf[spineLid] = leafDict
                
                
        print

    #----------------------------------------

    def __getPort(self, record):
        ports = record["ports"]
        count = len(ports)
        index = record["index"]
        
        record["index"] += 1
        
        return ports[index % count]
        

    def getLeafPortConnectedToSpine(self, leafSwitchLid, spineSwitchLid):
        # returns a port going to spine switch from list of available ports in a round-robin manner
        return self.__getPort(self.leafToSpine[leafSwitchLid][spineSwitchLid])
    

    def getSpinePortConnectedToLeaf(self, spineSwitchLid, leafSwitchLid):
        # returns a port going to leaf switch from list of available ports in a round-robin manner
        return self.__getPort(self.spineToLeaf[spineSwitchLid][leafSwitchLid])
    

    def getLeafToSpineUtilization(self, leafSwitchLid, spineSwitchLid):
        # returns a number of used links between leaf and spine switch (if the number returned is higher than the number of physical links, then the links are oversubscribed)
        return self.leafToSpine[leafSwitchLid][spineSwitchLid]["index"]


    def getSpineToLeafUtilization(self, spineSwitchLid, leafSwitchLid):
        # returns a number of used links between spine and leaf switch (if the number returned is higher than the number of physical links, then the links are oversubscribed)
        return self.spineToLeaf[spineSwitchLid][leafSwitchLid]["index"]
    
#----------------------------------------------------------------------


class RoutingAlgoPetr:
    # performs the routing based on some cost functions

    #----------------------------------------

    def __init__(self, linkData, sourceLids, destLids, routeRankingFunc):
        self.linkData = linkData

        self.sourceLids = sourceLids
        self.destLids = destLids
        
        # find the LIDs of leaf and spine switches
        self.leafSwitchLIDs, self.spineSwitchLIDs = utils.findSwitchLIDs(linkData)
        assert len(self.leafSwitchLIDs) == 12
        assert len(self.spineSwitchLIDs) == 6

        # generate routing table objects
        self.fabricTable = FabricTable(linkData, self.leafSwitchLIDs, self.spineSwitchLIDs)

        # occupancy table
        self.occupancyTable = OccupancyTable(self.linkData)

        # Which spine switch to use for the next destination LIDs assignement (used, when __makeRoutes is run second time for non priority links)
        self.spineIndex = 0

        # the function defining the best route in each step
        # (this may also return a tuple to break ties)
        self.routeRankingFunc = routeRankingFunc

        self.occupancyTableMainRoutes = None

        self.graphVizText = None


        print "* Petr's algorithm configuration:"
        print "*   BUs   = %d" % len(self.destLids)
        print "*   RUs   = %d" % len(self.sourceLids)
        print "*   spine = %d" % len(self.spineSwitchLIDs)
        print "*   leaf  = %d" % len(self.leafSwitchLIDs)
        print

        print "* Phase 0: Creating switch to switch porrt mapping tables"
        self.switchToSwitchTable = SwitchToSwitchTable(self.leafSwitchLIDs, self.spineSwitchLIDs, self.fabricTable)

    #----------------------------------------

    def __addAllRoutesToDest(self, route, destLid):
        
        strict = True
        
        # Adding one route for destination destLid to the routing table
        self.fabricTable.addRoute(route, destLid, strict)
        
        # Updating the occupancy table
        # It seems that for that we need to create all routes, so we need to find all RUs connected to the local leaf switch

        inputLeafSwitchLid = route.inputLeafSwitchLid
        

        # We loop over all RUs (sourceLids) and test if they are local to the given inputLeafSwitch
        # It is not optimal, but OK for now
        for sourceLid in self.sourceLids:
            # If RU is local on the leaf switch, add route into the occupancy table
            if self.fabricTable.isHostLocalOnTheSwitch(inputLeafSwitchLid, sourceLid):
                #print >> sys.stderr,"  assigning route for sourceLid=%d destLid=%d:" % (sourceLid, destLid), route
                self.occupancyTable.addRoute(sourceLid, destLid, route)

    #----------------------------------------

    def __makeRoutes(self, destLids, useSpineSwitchLIDs):
        
        print "**** Phase 1: Assigning BUs to spine switches"

        # We spread destinations attached to one leaf switch across several spine switched.
        # In order to do that, we make list of destinations (BUs) attached on one leaf switch, then to the next leaf and so on so
        # When assigning destinations to spine switches, we take destinations from previously created list in round robin way
        
        # Create a list of destinations (BUs) from leaf switches    
        destLidsSorted = []
        
        # Counts how many leaf switches are used (contains one or more active destinations)
        leafSwitchesUsed = 0

        print "* Looking at BU to leaf switch connections:"
        print "* leaf: [BUs]"
        for leafSwitchLid in self.leafSwitchLIDs:
            print "* %2d:" % leafSwitchLid,
            destList = []
            for destLid in destLids:

                # Test if destLid is local to the leafSwitch
                if leafSwitchLid == self.fabricTable.findLeafSwitchFromHostLid(destLid).switchLid:
                    destList.append(destLid)
                    
            print destList
            destLidsSorted += destList
            if len(destList) > 0:
                leafSwitchesUsed += 1
        print
            
        print "* Assigning BUs to spine switches:"

        # BU to spine switch assignement
        buToSpine = {}
        
        # BU to leaf switch table, where the BU is local
        buToLeaf = {}
        
        for lid in destLidsSorted:
            buToSpine[lid] = useSpineSwitchLIDs[self.spineIndex % len(useSpineSwitchLIDs)]
            self.spineIndex += 1
            
            # Find leaf switch, where BU is local
            leafSwitch = self.fabricTable.findLeafSwitchFromHostLid(lid).switchLid
            buToLeaf[lid] = leafSwitch
            
            
        print "*   %d BUs assigned to %d spine switches" % (len(destLids), len(self.spineSwitchLIDs))
    
        if len(destLids) > len(self.leafSwitchLIDs) and leafSwitchesUsed < len(self.leafSwitchLIDs):
            print "*   --> WARNING: %d BUs are spread over only %d out of %d leaf switches, this BU configuration may not be optimal" % (len(destLids), leafSwitchesUsed, len(self.leafSwitchLIDs)) 
        
        
        print
        print "* BU to spine switch assignment:"
        print "* [spine]: BUs"
        for spineLid in self.spineSwitchLIDs:
            print "* [%2d]:" % spineLid,
            for lid in destLidsSorted:
                if spineLid == buToSpine[lid]:
                    print "%4d " % lid,
            print
            
        print

        #
        ## Calculate how many destinations (BUs) are connected to the same leaf switch, per spine switch
        leafOccupancy = dict( (leaf, 0) for leaf in self.leafSwitchLIDs ) 
        
        # If there are more than 3 destinations assigned to the same leaf
        occupancyError = False

        print "* [spine]: number of connections per leaf switch"
        for spineLid in self.spineSwitchLIDs:
            print "* [%2d]:" % spineLid,
            
            leafOccupancy = dict( (leaf, 0) for leaf in self.leafSwitchLIDs ) 
            for lid in destLids:
                if spineLid == buToSpine[lid]:
                    leafOccupancy[ buToLeaf[lid] ] += 1
                    if leafOccupancy[ buToLeaf[lid] ] > 3:
                        occupancyError = True
            print leafOccupancy.values()
        
        
        if occupancyError:
            print "*   --> ERROR: There is a spine switch having more than 3 destinations on the same leaf switch! That will create a congestion!"
        print

      
        #----------


        print "**** Phase 2: Going from leaf to spine switches (assigning routes to leaf switches)"
        
#        leaf = get a leaf switch
#        for dest in all destinations:
#            if dest is local to leaf:
#                get local port for dest
#                assgin port
#                continue
#            spine = get spine switch for destination dest
#            get port for spine <- this function should automatically round robin the available ports
#            assign port
 
        for inputLeafSwitchLid in self.leafSwitchLIDs:
            print "* leaf %d" % inputLeafSwitchLid

            # for each leaf switch we loop over all destinations and try to assign outgoing ports...
            for destLid in destLids:
                if self.fabricTable.isHostLocalOnTheSwitch(inputLeafSwitchLid, destLid):
                    # Destinations local to a given leaf switch are skipped (are already assigned)
                    continue
                
                # get spine switch for the given destLid
                spineSwitchLid = buToSpine[destLid]
                
                # get port number on the leaf switch connected to a given spine switch
                inputLeafSwitchPort = self.switchToSwitchTable.getLeafPortConnectedToSpine(inputLeafSwitchLid, spineSwitchLid)
                
                ###
                ## Experimental, add spine to leaf route
                ## Normally, we would assign spine to leaf routes after all leaf to spine are processed
                ## However, this would break occupancy counting as is defined in this framework, so let's try to do it here
                ###
                
                # Get the local leaf switch for BU
                destLeafSwitchLid = buToLeaf[destLid]
                
                # Check if there already is a route from spine
                spineSwitchPort = self.fabricTable.getSwitchRouteOutputPortForDestination(spineSwitchLid, destLid)
                if spineSwitchPort == None:           
                    # if not, then make a new one
                    spineSwitchPort = self.switchToSwitchTable.getSpinePortConnectedToLeaf(spineSwitchLid, destLeafSwitchLid)
                                
                
                if False:
                    print "*   BU %4d: [leaf %2d]:%d -> [spine %2d]:%2d -> [leaf %2d]" % (destLid, inputLeafSwitchLid, inputLeafSwitchPort, spineSwitchLid, spineSwitchPort, destLeafSwitchLid)
                
                route = Route(self.linkData, inputLeafSwitchLid, inputLeafSwitchPort, spineSwitchLid, spineSwitchPort)
                self.__addAllRoutesToDest(route, destLid)
                
            #print
        print
        
        
        #
        ## Calculate how many destinations (BUs) are connected to the same leaf switch, per spine switch
        
        # If there are more than 3 destinations assigned to the same leaf
        occupancyError = False
        print "* [spine]: number of connections per leaf switch"
        for spineLid in self.spineSwitchLIDs:
            print "* [%2d]:" % spineLid,
            
            leafOccupancy = {} 
            for leafLid in self.leafSwitchLIDs:
                leafOccupancy[ leafLid ] = self.switchToSwitchTable.getSpineToLeafUtilization(spineLid, leafLid)
                if leafOccupancy[ leafLid ] > 3:
                    occupancyError = True
            print leafOccupancy.values()
        
        
        if occupancyError:
            print "*   --> ERROR: There is a spine switch having more than 3 destinations on the same leaf switch! That will create a congestion!"
        print


        print "* [leaf]: number of connections per spine switch"
        for leafLid in self.leafSwitchLIDs:
            print "* [%2d]:" % leafLid,
            
            spineOccupancy = {} 
            for spineLid in self.spineSwitchLIDs:
                spineOccupancy[ spineLid ] = self.switchToSwitchTable.getLeafToSpineUtilization(leafLid, spineLid)
            print spineOccupancy.values()

        print
        
    #----------------------------------------

    def run(self):
               
        destLids = self.destLids
        useSpineSwitchLIDs = self.spineSwitchLIDs[0:6]
        #useSpineSwitchLIDs = self.spineSwitchLIDs[0:3]
        
        self.__makeRoutes(destLids, useSpineSwitchLIDs)       
 
        # make a copy of the occupancy table (for later printing)
        self.occupancyTableMainRoutes = self.occupancyTable.clone()

        # also generate the graphviz code now
        self.graphVizText = self.__makeGraphViz()


        ###
        # Remaining routes

        destLids = self.sourceLids
        #useSpineSwitchLIDs = self.spineSwitchLIDs[3:6]
        
        # Not necessary, but makes things a little bit easier to reproduce 
        #self.spineIndex = 0

        self.__makeRoutes(destLids, useSpineSwitchLIDs)       


    #----------------------------------------

    def __makeGraphViz(self):
        # :return: graphviz code representing the the link occupancy of the routes
        #          added so far

        import sys, os

        # this is not thread safe...
        sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network/"))

        import drawIBclos
        sys.path.pop(-1)

        import utils
        # get the LIDs of spine and leaf switches
        leafSwitches, spineSwitches = utils.findSwitchLIDs(self.linkData)

        # convert to device names
        leafSwitches  = [ self.linkData.getDeviceName(lid) for lid in leafSwitches ]
        spineSwitches = [ self.linkData.getDeviceName(lid) for lid in spineSwitches ]


        # get the full mapping of peer devices attached to each port of each switch

        for lid in self.linkData.switchLIDs:
            switchData = self.linkData.getSwitchDataFromLID(lid)

        closDrawer = drawIBclos.ClosDrawer(spineSwitches, leafSwitches,
                                           self.linkData.getSwitchToPCmapping(),
                                           self.linkData.getPeerDeviceMap())

        # keep a list of all edges so that we can determine the maximum
        # occupancy before adding them (to determine the scaling
        # of occupancy to pen width)
        edges = []

        # take occupancies from the OccupancyTable object
        occupancyTable = self.occupancyTableMainRoutes

        #----------
        # source host to input leaf occupancies
        #----------
        for key, occ in occupancyTable.sourceToInputLeafSwitchOccupancy.getItems():
            # key is sourceLid
            edges.append(dict(sourceLid = key, port = 1, occupancy = occ))

        #----------
        # output leaf switch to destination PC occupancy
        #----------

        for key, occ in occupancyTable.outputLeafSwitchToDestOccupancy.getItems():
            # key is (outputLeafSwitchLID, outputLeafSwitchPort)
            edges.append(dict(sourceLid = key[0], port = key[1], occupancy = occ))

        #----------
        # input leaf switch to spine switch occupancy
        #----------

        for key, occ in occupancyTable.inputLeafSwitchLIDandPortToNumRoutes.getItems():
            # key is (inputLeafSwitchLID, port)
            edges.append(dict(sourceLid = key[0], port = key[1], occupancy = occ))

        #----------
        # spine switch to output leaf switch occupancy
        #----------

        for key, occ in occupancyTable.spineSwitchLIDandPortToNumRoutes.getItems():
            # key is (spineSwitchLID, port)
            edges.append(dict(sourceLid = key[0], port = key[1], occupancy = occ))

        #----------
        # determine maximum occupancy
        #----------
        maxOcc = max([ edge['occupancy'] for edge in edges ])

        #----------
        # determine conversion from occupancy to pen width
        #----------
        
        maxPenWidth = 7
        # pen width for low or no traffic
        minPenWidth = 0.1

        penWidthScaling = drawIBclos.PenWidthScaling(minPenWidth,
                                                     maxPenWidth,
                                                     1, # minimum occupancy
                                                     maxOcc)

        #----------
        # make default edges dotted
        #----------
        for item in closDrawer.edges.values():
            for edge in item.values():
                edge['attrs'] = [ 'style=dotted']

        #----------
        # add edges to clos drawer
        #----------
        for edge in edges:
            sourceDeviceName = self.linkData.getDeviceName(edge['sourceLid'])

            # determine graphviz attributes
            attrs = penWidthScaling.makeEdgeAttributes(edge['occupancy'])
            closDrawer.edges[sourceDeviceName][edge['port']]['attrs'] = attrs

        # the output buffer to write to
        import StringIO
        os = StringIO.StringIO()

        # generate the graphviz code
        closDrawer.doPrint(os)

        return os.getvalue()
        

    #----------------------------------------
