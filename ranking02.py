#!/usr/bin/env python


#----------------------------------------------------------------------
class RouteRanking02:
    # does a fat tree like routing by assigning
    # traffic for a given BU on the same leaf switch

    def __init__(self, spineSwitchLIDs):
        # maps from destination LID to LID of spine switch
        self.buToSpineSwitch = {}
        self.spineSwitchLIDs = spineSwitchLIDs

    def __call__(self, occupancyTable, route, sourceLid, destLid):
        spineSwitchLid = route.spineSwitchLid

        if not self.buToSpineSwitch.has_key(destLid):
            # assign a new spine switch to this destination:
            # take the spine switch which currently has the fewest routes
            # going over it

            occupancy, switchLid = min([ (occupancyTable.spineSwitchLIDtoNumRoutes.getCountWithDefault(lid, 0), lid) for lid in self.spineSwitchLIDs ])

            self.buToSpineSwitch[destLid] = switchLid

        switchLid = self.buToSpineSwitch[destLid]

        if switchLid == route.spineSwitchLid:
            # this is the preferred route
            spineSwitchRanking = 0
        else:
            spineSwitchRanking = 1

        return (
            spineSwitchRanking,

            # secondary ranking
            occupancyTable.getSpineToLeafCableOccupancy(route),

            occupancyTable.getLeafToSpineCableOccupancy(route),
            )

#----------------------------------------------------------------------


def makeRouteRankingFunction(routingAlgoObj):
    return RouteRanking02(routingAlgoObj.spineSwitchLIDs)

#----------------------------------------------------------------------
    
