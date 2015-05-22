#!/usr/bin/env python

class Route:
    # represents a non-trivial route, i.e. one which goes from a leaf
    # to a spine switch and back to a leaf switch

    #----------------------------------------

    def __init__(self, linkData, inputLeafSwitchLid, inputLeafSwitchPort, spineSwitchLid, spineSwitchPort):
        # note that we also would need to add the input ports and the spine and output leaf
        # switch and the lid of the output leaf switch to be able to create the
        # reverse of this route

        # keep a link to this, this is always useful
        self.linkData = linkData

        
        self.inputLeafSwitchLid = inputLeafSwitchLid

        self.inputLeafSwitchPort = inputLeafSwitchPort

        self.spineSwitchLid = spineSwitchLid

        self.spineSwitchPort = spineSwitchPort

        #----------
        # these we don't need in principle but are sometimes useful e.g.
        # when getting the reverse route etc.
        #----------
        
        # find the LID of the original output leaf switch
        spineSwitchPortData = linkData.getSwitchPortData(self.spineSwitchLid, self.spineSwitchPort)

        self.outputLeafSwitchLid = spineSwitchPortData['peerLid']

        # the port where the cable came into the output leaf switch
        self.outputLeafSwitchPort = spineSwitchPortData['peerPort']

    #----------------------------------------

    def __str__(self):
        return "[inputLeafSwitch: lid=%d port=%d spineSwitch: lid=%d port=%d]" % (self.inputLeafSwitchLid,
                                                                                self.inputLeafSwitchPort,
                                                                                self.spineSwitchLid,
                                                                                self.spineSwitchPort,
                                                                                )

    #----------------------------------------

    def __repr__(self):
        return self.__str__()

    #----------------------------------------

    @staticmethod
    def reverse(route):
        # returns the reverse of this route

        linkData = route.linkData

        # find the input port (of the original route) to the spine switch
        inputLeafSwitchPortData = linkData.getSwitchPortData(route.inputLeafSwitchLid, route.inputLeafSwitchPort)

        spineSwitchInputPort = inputLeafSwitchPortData['peerPort']

        assert inputLeafSwitchPortData['peerLid'] == route.spineSwitchLid

        # the reverse route
        return Route(
            route.outputLeafSwitchLid,
            route.outputLeafSwitchPort,
            route.spineSwitchLid,
            spineSwitchInputPort)

    #----------------------------------------

