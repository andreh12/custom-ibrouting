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
        self.occupancyTable = OccupancyTable()

        # the function defining the best route in each step
        # (this may also return a tuple to break ties)
        self.routeRankingFunc = routeRankingFunc

        self.occupancyTableMainRoutes = None

    #----------------------------------------

    def __addRoute(self, route, sourceLid, destLid, strict):

        print >> sys.stderr,"assigning route for sourceLid=%d destLid=%d:" % (sourceLid, destLid), route

        # update the routing and occupancy table
        self.fabricTable.addRoute(route, destLid, strict)

        self.occupancyTable.addRoute(route)

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
            routesCost = [ self.routeRankingFunc(self.occupancyTable, route) for route in routes ]

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

        # now rerun over all possible pairs to build routes
        # (between the hosts, not sure whether we also need
        # routing table entries from switch to switch)

        self.__makeRoutes(otherPairs, strict = False)

        # self.fabricTable.addRoute(Route.reverse(self.linkData, route), sourceLid, strict = False)


    #----------------------------------------

