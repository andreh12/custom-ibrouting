#!/usr/bin/env python


# from OccupancyTable import OccupancyTable
# from Cable import Cable
from Route import Route

from RoutingTable import RoutingTable

#----------------------------------------------------------------------

class FabricTable:
    # keeps a list of all routing tables
    # and adds some additional functionality

    #----------------------------------------

    def __init__(self, linkData, leafSwitchLids, spineSwitchLids):

        # the structure of the fabric
        self.linkData = linkData

        self.leafSwitchLids = set(leafSwitchLids)
        self.spineSwitchLids = set(spineSwitchLids)

        # generate routing table objects
        self.routingTables = {}
        for lid in leafSwitchLids + spineSwitchLids:
            self.routingTables[lid] = RoutingTable(linkData, lid)

    #----------------------------------------

    def findLeafSwitchFromHostLid(self, hostLid):

        for leafSwitchLid in self.leafSwitchLids:

            routingTable = self.routingTables[leafSwitchLid]

            if routingTable.isConnectedToLid(hostLid):
                return routingTable

        # not found
        return None

    #----------------------------------------

    def findExistingRoute(self, sourceLid, destLid):
        # returns a Route object if there is already
        # a route configured for this or None
        # if not
        #
        # do NOT call this when sourceLid and destLid
        # are on the same leaf switch !

        inputLeafSwitch = self.findLeafSwitchFromHostLid(sourceLid)
        assert inputLeafSwitch != None

        # find the output switch
        outputLeafSwitch = self.findLeafSwitchFromHostLid(destLid)
        assert outputLeafSwitch != None

        if inputLeafSwitch == outputLeafSwitch:
            raise Exception("source and destination lid are connected to the same leaf switch, this is not supported here")

        #----------
        # input leaf to spine switch
        #----------
        inputLeafSwitchPort = inputLeafSwitch.getOutputPortForDestination(destLid)

        if inputLeafSwitchPort == None:
            # no route defined yet
            return None

        # find which spine switch is connected to this port
        # spineSwitchLid = linkData.getSwitchPortData(inputLeafSwitch.switchLid, inputLeafSwitchPort)['peerLid']
        spineSwitchLid = inputLeafSwitch.localLIDs[inputLeafSwitchPort]

        spineSwitch = self.routingTables[spineSwitchLid]

        #----------
        # spine switch back to output leaf switch
        #----------

        spineSwitchPort = spineSwitch.getOutputPortForDestination(destLid)

        if spineSwitchPort == None:
            # no route defined yet on the spine switch
            # we should actually never come here, this means that
            # a non-local route was only partially set up ?
            return None

        return Route(self.linkData,
                     inputLeafSwitch.switchLid,
                     inputLeafSwitchPort,
                     spineSwitchLid,
                     spineSwitchPort)

    #----------------------------------------

    def makeRoutes(self, sourceLid, destLid):
        # returns a list of possible routes between the two LIDs
        # returns None if the source and destination LID are on the same leaf switch

        # find the input leaf switch the source LID is connected to

        inputLeafSwitch = self.findLeafSwitchFromHostLid(sourceLid)
        assert inputLeafSwitch != None

        # find the output switch
        outputLeafSwitch = self.findLeafSwitchFromHostLid(destLid)
        assert outputLeafSwitch != None

        if inputLeafSwitch == outputLeafSwitch:
            # can be forwarded within the same leaf switch, does not
            # go over cables
            return None

        # check if we already have a route defined to this
        # destination LID
        # if yes, return it (and only this one)

        route = self.findExistingRoute(sourceLid, destLid)
        if route != None:
            # a route exists already
            return [ route ]

        #----------
        # build all possible routes
        #----------

        retval = []

        # loop over all ports of the input leaf switch
        for inputLeafSwitchPort, spineSwitchLid in inputLeafSwitch.localLIDs.items():

            if not spineSwitchLid in self.spineSwitchLids:
                # other end is not a spine switch
                continue

            # find the spine switch for this LID
            spineSwitch = self.routingTables[spineSwitchLid]

            # check if the spine switch already has an entry for the
            # destination LID (which we must take if it exists)
            spineSwitchPort = spineSwitch.getOutputPortForDestination(destLid)

            if spineSwitchPort != None:
                # a routing table entry exists already for this destination
                # on this spine switch
                allowedSpineSwitchPorts = [ spineSwitchPort ]
            else:
                allowedSpineSwitchPorts = spineSwitch.localLIDs.keys()

            # loop over all cables back to the spine switch

            for spineSwitchPort in allowedSpineSwitchPorts:

                peerLid = spineSwitch.localLIDs[spineSwitchPort]

                if peerLid != outputLeafSwitch.switchLid:
                    # this cable does not go back to the proper output leaf switch
                    continue

                retval.append(
                  Route(self.linkData,
                        inputLeafSwitch.switchLid,
                        inputLeafSwitchPort,
                        spineSwitchLid,
                        spineSwitchPort)
                )

        return retval

    #----------------------------------------

    def addRoute(self, route, destLid, strict = True):
        # if strict is True, tries to assign the given route
        # (will lead to an exception if already existing)
        #
        # if strict is False, will stop as soon as
        # a routing table is encountered which already has
        # an entry for the destination lid

        inputLeafSwitch = self.routingTables[route.inputLeafSwitchLid]

        # update routing table on input leaf switch
        assigned = inputLeafSwitch.addLocalRoute(destLid, route.inputLeafSwitchPort, strict)

        if not assigned:
            return

        # update routing table on spine switch
        spineSwitch = self.routingTables[route.spineSwitchLid]

        spineSwitch.addLocalRoute(destLid, route.spineSwitchPort, strict)

        # no need to update the routing table on the output leaf switch:
        # this is a local route there which should have been set
        # in the beginning


    #----------------------------------------


    def doPrint(self, os):
        for routingTable in self.routingTables.values():
            routingTable.doPrint(os)

    #----------------------------------------



#----------------------------------------------------------------------

