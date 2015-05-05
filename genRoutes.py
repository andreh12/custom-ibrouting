#!/usr/bin/env python

# tool to parse generate our custom Infiniband routing table

import sys, os, commands
from pprint import pprint

sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network/"))

import iblinkStatusUtils 

#----------------------------------------------------------------------
iblinkInfoExe = "/usr/sbin/iblinkinfo"

# from ~/2012-06-infiniband/config-cdaq-2015-04-02.py
# (44x44)
sourceHosts = ['ru-c2e13-22-01', 'ru-c2e13-23-01', 'ru-c2e15-19-01', 'ru-c2e12-16-01', 'ru-c2e12-17-01', 'ru-c2e12-18-01', 'ru-c2e13-27-01', 'ru-c2e13-28-01', 'ru-c2e13-29-01', 'ru-c2e15-27-01', 'ru-c2e12-10-01', 'ru-c2e12-11-01', 'ru-c2e12-12-01', 'ru-c2e12-27-01', 'ru-c2e12-28-01', 'ru-c2e12-29-01', 'ru-c2e14-27-01', 'ru-c2e12-13-01', 'ru-c2e12-14-01', 'ru-c2e12-15-01', 'ru-c2e12-24-01', 'ru-c2e12-25-01', 'ru-c2e12-26-01', 'ru-c2e13-16-01', 'ru-c2e13-17-01', 'ru-c2e13-18-01', 'ru-c2e15-16-01', 'ru-c2e13-10-01', 'ru-c2e13-11-01', 'ru-c2e13-12-01', 'ru-c2e13-13-01', 'ru-c2e13-14-01', 'ru-c2e13-15-01', 'ru-c2e15-13-01', 'ru-c2e12-19-01', 'ru-c2e13-24-01', 'ru-c2e13-30-01', 'ru-c2e13-34-01', 'ru-c2e15-30-01', 'ru-c2e15-34-01', 'ru-c2e15-35-01', 'ru-c2e12-30-01', 'ru-c2e12-35-01', 'ru-c2e14-30-01']

destHosts = ['bu-c2f16-35-01', 'bu-c2e18-35-01', 'bu-c2d33-30-01', 'bu-c2d41-30-01', 'bu-c2d42-30-01', 'bu-c2f16-31-01', 'bu-c2e18-31-01', 'bu-c2d33-20-01', 'bu-c2d41-20-01', 'bu-c2d35-30-01', 'bu-c2f16-11-01', 'bu-c2e18-11-01', 'bu-c2d31-20-01', 'bu-c2d36-20-01', 'bu-c2e18-23-01', 'bu-c2e18-25-01', 'bu-c2f13-29-01', 'bu-c2f16-13-01', 'bu-c2e18-13-01', 'bu-c2d31-30-01', 'bu-c2d36-30-01', 'bu-c2d34-10-01', 'bu-c2d34-20-01', 'bu-c2f16-17-01', 'bu-c2e18-17-01', 'bu-c2d32-10-01', 'bu-c2d37-10-01', 'bu-c2d38-10-01', 'bu-c2d38-20-01', 'bu-c2f16-37-01', 'bu-c2e18-39-01', 'bu-c2d35-20-01', 'bu-c2d42-20-01', 'bu-c2f16-29-01', 'bu-c2e18-29-01', 'bu-c2d33-10-01', 'bu-c2d41-10-01', 'bu-c2e18-41-01', 'bu-c2e18-43-01', 'bu-c2f16-09-01', 'bu-c2e18-09-01', 'bu-c2d31-10-01', 'bu-c2d36-10-01', 'bu-c2f16-23-01']

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


# from RoutingTable import RoutingTable


#----------------------------------------------------------------------




#----------------------------------------------------------------------

from FabricTable import FabricTable
from OccupancyTable import OccupancyTable

class RoutingAlgo:
    # performs the routing based on some cost functions

    #----------------------------------------

    def __init__(self, linkData, sourceLids, destLids, routeRankingFunc):
        self.sourceLids = sourceLids
        self.destLids = destLids

        # find the LIDs of leaf and spine switches
        self.leafSwitchLIDs, self.spineSwitchLIDs = findSwitchLIDs(linkData)
        assert len(self.leafSwitchLIDs) == 12
        assert len(self.spineSwitchLIDs) == 6

        # generate routing table objects
        self.fabricTable = FabricTable(linkData, self.leafSwitchLIDs, self.spineSwitchLIDs)

        # occupancy table
        self.occupancyTable = OccupancyTable()

        # the function defining the best route in each step
        # (this may also return a tuple to break ties)
        self.routeRankingFunc = routeRankingFunc

    #----------------------------------------

    def __addRoute(self, route, sourceLid, destLid):

        print >> sys.stderr,"assigning route for sourceLid=%d destLid=%d:" % (sourceLid, destLid), route

        # update the routing and occupancy table
        self.fabricTable.addRoute(route, destLid)

        self.occupancyTable.addRoute(route)


    #----------------------------------------

    def run(self):

        import itertools

        # itertools.product(..) does not exist on SLC5
        # allPairs = itertools.product(self.sourceLids, self.destLids)

        allPairs = [ (src, dst) for src in self.sourceLids for dst in self.destLids ]

        while allPairs:
            sourceLid, destLid = allPairs.pop(0)

            assert sourceLid != destLid

            routes = self.fabricTable.makeRoutes(sourceLid, destLid)

            # if these are on the same switch, routes is None
            if routes == None:
                continue

            # pick the route based on some occupancy measure,
            # i.e. pick the 'smallest' element
            routesCost = [ self.routeRankingFunc(self.occupancyTable, route) for route in routes ]

            bestRouteCost, bestRoute = min(zip(routesCost, routes))

            # add this route to the routing table
            self.__addRoute(bestRoute, sourceLid, destLid)

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
                self.__addRoute(bestRoute, sourceLid2, destLid2)

                # remove this pair
                allPairs.pop(index)


            # TODO: also put reverse path !

        # loop over all pairs of (source, destination)


    #----------------------------------------


#----------------------------------------------------------------------


def routeRanking01(occupancyTable, route):

    # return a tuple of (spineSwitchOccupancy, spineToLeafCableOccupancy, leafToSpineCableOccupancy)

    return (occupancyTable.getSpineSwitchOccupancy(route),
            occupancyTable.getLeafToSpineCableOccupancy(route),
            occupancyTable.getSpineToLeafCableOccupancy(route))


#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
ARGV = sys.argv[1:]

if len(ARGV) == 1:
    # read the output of iblinkinfo from the given file
    linkData = iblinkStatusUtils.IBlinkStatusData(open(ARGV[0]).read())
elif len(ARGV) == 0:
    # run iblinkinfo ourselves
    if not os.path.exists(iblinkInfoExe):
        print "this host does not have " + iblinkInfoExe + ". Are you running on a host connected to the Infiniband network ?"
        sys.exit(1)

    linkData = iblinkStatusUtils.IBlinkStatusData(commands.getoutput("/usr/bin/sudo " + iblinkInfoExe))
else:
    print >> sys.stderr,"wrong number of command line arguments"
    sys.exit(1)

#----------------------------------------

# convert host names to LIDs
sourceLids = [ linkData.getLidFromHostname(host) for host in sourceHosts ]
destLids   = [ linkData.getLidFromHostname(host) for host in destHosts   ]


routingAlgo = RoutingAlgo(linkData, sourceLids, destLids, routeRanking01)

routingAlgo.run()

# TEST
if False:
    routes = fabricTable.makeRoutes(sourceLids[0], destLids[0])
    pprint(routes)
    print len(routes)



routingAlgo.fabricTable.doPrint(sys.stdout)
#----------------------------------------
