#!/usr/bin/env python

import sys

# python has a similar class but only from 2.7 on...
class Counter:

    def __init__(self):
        self.counts = {}

    def inc(self, key, increment = 1):
        self.counts[key] = self.counts.get(key, 0) + increment

    def getCount(self, key):
        return self.counts[key]

    def getCountWithDefault(self, key, defaultValue):
        return self.counts.get(key, defaultValue)

    def getKeys(self):
        return self.counts.keys()

    def getItems(self):
        return self.counts.items()

    def getOccupancyHistogram(self, reverse = False):
        # returns a list with entries [ (count, number of items with this count) ]
        # ordered in increasing order of count
        retval = []

        cnt = Counter()

        for c in self.counts.values():
            cnt.inc(c)

        for count in sorted(cnt.counts.keys(), reverse = reverse):
            retval.append((count, cnt.counts[count]))

        return retval

    def clone(self):

        # produce a copy of self.counts (but do not deeply clone
        # the keys

        retval = Counter()
        retval.counts = dict(self.counts)

        return retval



#----------------------------------------------------------------------


class OccupancyTable:
    # class for keeping track of number of connections
    # going through a given cable and spine switch

    #----------------------------------------

    def __init__(self, linkData):

        self.linkData = linkData

        # for keeping statistics about how many routes
        # go through the spine switches
        self.spineSwitchLIDtoNumRoutes = Counter()

        # key is (inputLeafSwitchLID, port)
        # value is number of routes
        self.inputLeafSwitchLIDandPortToNumRoutes = Counter()

        # key is (spineSwitchLID, port)
        self.spineSwitchLIDandPortToNumRoutes = Counter()

        #----------

        # counts input PCs to input leaf switch link occupancies
        # key is sourceLid
        self.sourceToInputLeafSwitchOccupancy = Counter()

        # counts output leaf switch to destination PCs occupancies
        # key is (outputLeafSwitchLID, outputLeafSwitchPort)
        self.outputLeafSwitchToDestOccupancy = Counter()

    #----------------------------------------

    def clone(self):

        retval = OccupancyTable(self.linkData)

        retval.spineSwitchLIDtoNumRoutes            = self.spineSwitchLIDtoNumRoutes.clone()
        retval.inputLeafSwitchLIDandPortToNumRoutes = self.inputLeafSwitchLIDandPortToNumRoutes.clone()
        retval.spineSwitchLIDandPortToNumRoutes     = self.spineSwitchLIDandPortToNumRoutes.clone()

        retval.sourceToInputLeafSwitchOccupancy     = self.sourceToInputLeafSwitchOccupancy.clone()
        retval.outputLeafSwitchToDestOccupancy      = self.outputLeafSwitchToDestOccupancy.clone()

        return retval

    #----------------------------------------

    def addRoute(self, sourceLid, destLid, route):

        # update spine switch occupancy
        self.spineSwitchLIDtoNumRoutes.inc(route.spineSwitchLid)

        # update leaf to spine switch cable occupancy
        self.inputLeafSwitchLIDandPortToNumRoutes.inc((route.inputLeafSwitchLid, route.inputLeafSwitchPort))

        # update spine to leaf switch cable occupancy
        self.spineSwitchLIDandPortToNumRoutes.inc((route.spineSwitchLid, route.spineSwitchPort))

        #-----
        
        # update source to input leaf switch occupancy
        self.sourceToInputLeafSwitchOccupancy.inc(sourceLid)

        # update source to input leaf switch occupancy
        # first find the output leaf switch

        outputLeafSwitchLID = self.linkData.getSwitchPortData(route.spineSwitchLid, route.spineSwitchPort)['peerLid']
        
        # find the output port on the output leaf switch to go to the destination LID
        outputPortData = self.linkData.findSwitchPortByPeerLid(outputLeafSwitchLID, destLid)
        assert outputPortData != None

        self.outputLeafSwitchToDestOccupancy.inc((outputLeafSwitchLID, outputPortData['port']))

    #----------------------------------------

    def getSpineSwitchOccupancy(self, route):
        return self.spineSwitchLIDtoNumRoutes.getCountWithDefault(route.spineSwitchLid, 0)

    #----------------------------------------

    def getLeafToSpineCableOccupancy(self, route):

        return self.inputLeafSwitchLIDandPortToNumRoutes.getCountWithDefault((route.inputLeafSwitchLid, route.inputLeafSwitchPort), 0)

    #----------------------------------------

    def getSpineToLeafCableOccupancy(self, route):
        return self.spineSwitchLIDandPortToNumRoutes.getCountWithDefault((route.spineSwitchLid, route.spineSwitchPort), 0)

    #----------------------------------------

    def printSummary(self, os = sys.stdout, showPlots = True):
        if showPlots:
            import pylab

        print >> os,"spine switch occupancies:"

        xvalues = []; yvalues = []

        for occupancy, numItems in self.spineSwitchLIDtoNumRoutes.getOccupancyHistogram(reverse = True):
            print >> os,"  %4d switches have %4d paths" % (numItems, occupancy)
            xvalues.append(occupancy); yvalues.append(numItems)

        if showPlots:
            pylab.figure(facecolor = 'white')
            pylab.bar(xvalues, yvalues, align = 'center')
            pylab.title('routes per spine switch')
            pylab.grid()
            pylab.xlabel("number of routes")
            pylab.ylabel("number of switches")

        #----------

        print >> os
        print >> os,"spine to leaf cable occupancies:"

        xvalues = []; yvalues = []
        for occupancy, numItems in self.spineSwitchLIDandPortToNumRoutes.getOccupancyHistogram(reverse = True):
            print >> os,"  %4d cables have %4d paths" % (numItems, occupancy)

            xvalues.append(occupancy); yvalues.append(numItems)

        if showPlots:
            pylab.figure(facecolor = 'white')
            pylab.bar(xvalues, yvalues, align = 'center')
            pylab.title('routes per spine to leaf cable')
            pylab.grid()
            pylab.xlabel("number of routes")
            pylab.ylabel("number of cables")

        #----------

        print >> os
        print >> os,"leaf to spine cable occupancies:"

        xvalues = []; yvalues = []
        for occupancy, numItems in self.inputLeafSwitchLIDandPortToNumRoutes.getOccupancyHistogram(reverse = True):
            print >> os,"  %4d cables have %4d paths" % (numItems, occupancy)

            xvalues.append(occupancy); yvalues.append(numItems)
            
        if showPlots:
            pylab.figure(facecolor = 'white')
            pylab.bar(xvalues, yvalues, align = 'center')
            pylab.title('routes per leaf to spine cable')
            pylab.grid()
            pylab.xlabel("number of routes")
            pylab.ylabel("number of cables")

    #----------------------------------------

