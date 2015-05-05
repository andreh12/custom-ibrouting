#!/usr/bin/env python


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

#----------------------------------------------------------------------


class OccupancyTable:
    # class for keeping track of number of connections
    # going through a given cable and spine switch

    #----------------------------------------

    def __init__(self):

        # for keeping statistics about how many routes
        # go through the spine switches
        self.spineSwitchLIDtoNumRoutes = Counter()

        # key is (inputLeafSwitchLID, port)
        # value is number of routes
        self.inputLeafSwitchLIDandPortToNumRoutes = Counter()

        # key is (spineSwitchLID, port)
        self.spineSwitchLIDandPortToNumRoutes = Counter()

    #----------------------------------------

    def addRoute(self, route):

        # update spine switch occupancy
        self.spineSwitchLIDtoNumRoutes.inc(route.spineSwitchLid)

        # update leaf to spine switch cable occupancy
        self.inputLeafSwitchLIDandPortToNumRoutes.inc((route.inputLeafSwitchLid, route.inputLeafSwitchPort))

        # update spine to leaf switch cable occupancy
        self.spineSwitchLIDandPortToNumRoutes.inc((route.spineSwitchLid, route.spineSwitchPort))


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
