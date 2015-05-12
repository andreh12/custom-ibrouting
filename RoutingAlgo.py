#!/usr/bin/env python

import sys

from FabricTable import FabricTable
from OccupancyTable import OccupancyTable
import utils

#----------------------------------------------------------------------

class RoutingAlgo:
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

        # the function defining the best route in each step
        # (this may also return a tuple to break ties)
        self.routeRankingFunc = routeRankingFunc

        self.occupancyTableMainRoutes = None

        self.graphVizText = None

    #----------------------------------------

    def __addRoute(self, route, sourceLid, destLid, strict):

        print >> sys.stderr,"assigning route for sourceLid=%d destLid=%d:" % (sourceLid, destLid), route

        # update the routing and occupancy table
        self.fabricTable.addRoute(route, destLid, strict)

        self.occupancyTable.addRoute(sourceLid, destLid, route)

        # also add the reverse route but don't count it in the occupancy table
        # (the traffic back from the BUs to the RUs is much smaller)
        # self.fabricTable.addRoute(Route.reverse(self.linkData, route), sourceLid, strict = False)

    #----------------------------------------

    def __makeRoutes(self, allPairs, strict):
        # @param allPairs is a list of (sourceLid, destLid) pairs

        # make a copy which we can modify
        allParis = allPairs[:]

        while allPairs:
            sourceLid, destLid = allPairs.pop(0)

            if sourceLid == destLid:
                # no route needed for loopback...
                continue

            routes = self.fabricTable.makeRoutes(sourceLid, destLid)

            # if these are on the same switch, routes is None
            if routes == None:
                continue

            # if a route already has been fully defined,
            # routes will just contain one entry

            # pick the route based on some occupancy measure,
            # i.e. pick the 'smallest' element
            routesCost = [ self.routeRankingFunc(self.occupancyTable, route, sourceLid, destLid) for route in routes ]

            bestRouteCost, bestRoute = min(zip(routesCost, routes))

            # add this route to the routing table
            self.__addRoute(bestRoute, sourceLid, destLid, strict)

            # now we must update other occupancies to the same destination lid:
            #
            #  - sources on the same input leaf switch will take exactly
            #    the same cables and spine switch
            #
            #  - sources going over the same spine switch will take
            #    the same cable to the output leaf switch but we're
            #    still free to choose a leaf switch for later routes, so we
            #    don't update these now

            # find remaining pairs with a LID on the same leaf input
            # switch and going to the same destination LID
            inputLeafSwitch = self.fabricTable.findLeafSwitchFromHostLid(sourceLid)

            for index in reversed(range(len(allPairs))):
                sourceLid2, destLid2 = allPairs[index]

                if destLid2 != destLid:
                    # not going to the same destination
                    continue

                if not inputLeafSwitch.isConnectedToLid(sourceLid2):
                    # not on the same input leaf switch
                    continue

                # do not assign the same route twice
                # (this actually should not happen)
                assert sourceLid2 != sourceLid;

                # add the same route for this also
                self.__addRoute(bestRoute, sourceLid2, destLid2, strict)

                # remove this pair
                allPairs.pop(index)

        # loop over all pairs of (source, destination)

    #----------------------------------------

    def run(self):

        priorityPairs = [ ]
        otherPairs = []

        # make the high priority routes: from the involved RUs to the BUs
        for src in self.linkData.hostLIDs:

            srcIsPrio = (src in self.sourceLids)

            for dst in self.linkData.hostLIDs:

                if srcIsPrio and dst in self.destLids:
                    priorityPairs.append((src, dst))
                else:
                    otherPairs.append((src, dst))

        self.__makeRoutes(priorityPairs, strict = True)

        # make a copy of the occupancy table (for later printing)
        self.occupancyTableMainRoutes = self.occupancyTable.clone()

        # also generate the graphviz code now
        self.graphVizText = self.__makeGraphViz()


        # now rerun over all possible pairs to build routes
        # (between the hosts, not sure whether we also need
        # routing table entries from switch to switch)

        self.__makeRoutes(otherPairs, strict = False)

        # self.fabricTable.addRoute(Route.reverse(self.linkData, route), sourceLid, strict = False)


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
