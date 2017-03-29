#!/usr/bin/env python


# from OccupancyTable import OccupancyTable
# from Cable import Cable
from Route import Route
import sys

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

    def isHostLocalOnTheSwitch(self, switchLid, hostLid):

        # returns True is if the hostLid it local to switchLid (is directly attached to that switch)

        routingTable = self.routingTables[switchLid]

        assert routingTable != None

        return routingTable.isConnectedToLid(hostLid);
                                                       
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
    def findLocalPortsForDestination(self, switchLid, destLid):
        # returns list of all output ports on the given switch physically connected to the given destination

        routingTable = self.routingTables[switchLid]

        assert routingTable != None

        return routingTable.findLocalPorts(destLid);

    #----------------------------------------

    def getSwitchRouteOutputPortForDestination(self, switchLid, destLid):

        # checks if there already is a route from a switch to destLid and returns output port
        # returns none if route is not define

        routingTable = self.routingTables[switchLid]

        assert routingTable != None

        return routingTable.getOutputPortForDestination(destLid)

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

    def makeInterSwitchRoutes(self):
        # make some routes between the spine and leaf switches (and reverse direction)
        # this is needed e.g. by ibqueryerrors
        #
        # also makes routes from leaf to leaf and from spine to spine switches
        # 
        # note that these routes are just produced
        # on a round robin basis, nothing is optimized
        # here assuming that there is not much traffic there anyway

        # count newly assigned routes
        localRoutesAssigned = 0

        for sourceLids, destLids in (
            (self.leafSwitchLids, self.spineSwitchLids),
            (self.spineSwitchLids, self.leafSwitchLids),
            ):

            for sourceLid in sourceLids:
                
                sourceSwitch = self.routingTables[sourceLid]

                for destIndex, destLid in enumerate(destLids):

                    # check that there is not already a route defined for this
                    # LID (this should not happen actually)
                    # assert sourceSwitch.getOutputPortForDestination(destLid) == None, "a route from %d to %d has been assigned already" % (sourceLid, destLid)

                    if sourceSwitch.getOutputPortForDestination(destLid) != None:
                        # route already assigned. This normally happens
                        # for direct connections (leaf to spine or spine to leaf)
                        continue

                    # normally we should never come here because local routes have been assigned already
                    
                    localRoutesAssigned += 1

                    # get all ports which are connected to the peer switch
                    ports = sourceSwitch.findLocalPorts(destLid)

                    assert len(ports) >= 1
                    
                    # in our setup at P5 we have 3 ports between any 
                    # pair of leaf / spine switch
                    assert len(ports) == 3

                    # just take the first port if not assigned yet
                    sourceSwitch.addLocalRoute(destLid, ports[0])

                    


        # now that we have the leaf to spine and spine to leaf routes
        # we can assign leaf to leaf and spine to spine routes
        # since now the spine switches have routes (output ports) to
        # all leaf switches and vice versa

        print >> sys.stderr, "spine <-> leaf localRoutesAssigned=",localRoutesAssigned
        
        #----------
        # now assign spine-spine and leaf-leaf routes
        #----------

        localRoutesAssigned = 0

        for lids, otherLayerLids in (
            (sorted(self.leafSwitchLids), sorted(self.spineSwitchLids)),
            (sorted(self.spineSwitchLids), sorted(self.leafSwitchLids)),
            ):

            otherLayerSwitchIndex = 0
            
            for sourceLid in lids:
                
                sourceSwitch = self.routingTables[sourceLid]

                for destIndex, destLid in enumerate(lids):

                    if sourceSwitch.getOutputPortForDestination(destLid) != None:
                        # route already assigned. This normally happens
                        # for direct connections (leaf to spine or spine to leaf)
                        continue

                    # check if sourceLid == destLid: then assign port 0
                    if sourceLid == destLid:
                        sourceSwitch.addLocalRoute(destLid, 0)
                        continue
                    
                    localRoutesAssigned += 1

                    # we would need something like self.makeRoutes(..)
                    # but makeRoutes is not designed to work from
                    # switch to switch
                    #
                    # pick one of the other layer's switches
                    # (which should have a switch to the final
                    # destination already)
                    
                    otherLayerLid = otherLayerLids[otherLayerSwitchIndex]
                    otherLayerSwitchIndex = (otherLayerSwitchIndex + 1) % len(otherLayerLids)

                    otherLayerSwitch = self.routingTables[otherLayerLid]

                    # make sure we have already a route to the other layer's switch
                    assert otherLayerSwitch.getOutputPortForDestination(destLid) != None, "other layer switch lid %d does not have a route to lid %d" % (otherLayerLid, destLid)

                    # for convenience, we just use the same port as we use
                    # for to reach the other layer's switch (which is not necessary,
                    # we could chose any of the other two ports)

                    # add the local route
                    port = sourceSwitch.lidToOutputPort[otherLayerLid]
                    sourceSwitch.addLocalRoute(destLid, port)


        print >> sys.stderr, "spine <-> spine / leaf <-> leaf localRoutesAssigned=",localRoutesAssigned


    #----------------------------------------


#----------------------------------------------------------------------

