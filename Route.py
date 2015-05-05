#!/usr/bin/env python

class Route:
    # represents a non-trivial route, i.e. one which goes from a leaf
    # to a spine switch and back to a leaf switch

    #----------------------------------------

    def __init__(self, inputLeafSwitchLid, inputLeafSwitchPort, spineSwitchLid, spineSwitchPort):
        # note that we also would need to add the input ports and the spine and output leaf
        # switch and the lid of the output leaf switch to be able to create the
        # reverse of this route

        self.inputLeafSwitchLid = inputLeafSwitchLid

        self.inputLeafSwitchPort = inputLeafSwitchPort

        self.spineSwitchLid = spineSwitchLid

        self.spineSwitchPort = spineSwitchPort

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
    def reverse(linkData, route):
        # returns the reverse of this route

        # find the LID of the original output leaf switch
        spineSwitchPort = linkData.getSwitchPortData(route.spineSwitchLid, route.spineSwitchPort)

        outputLeafSwitchLid = spineSwitchPort['peerLid']

        # the port where the cable came into the output leaf switch
        outputLeafSwitchPort = spineSwitchPort['peerPort']

        # find the input port (of the original route) to the spine switch

        inputLeafSwitchPort = linkData.getSwitchPortData(route.inputLeafSwitchLid, route.inputLeafSwitchPort)

        spineSwitchInputPort = inputLeafSwitchPort['peerPort']

        assert inputLeafSwitchPort['peerLid'] == route.spineSwitchLid

        # the reverse route
        return Route(
            outputLeafSwitchLid,
            outputLeafSwitchPort,
            route.spineSwitchLid,
            spineSwitchInputPort)

    #----------------------------------------

