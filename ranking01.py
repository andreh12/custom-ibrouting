#!/usr/bin/env python


#----------------------------------------------------------------------
def routeRanking01(occupancyTable, route, sourceLid, destLid):

    # @return a tuple of (spineSwitchOccupancy, spineToLeafCableOccupancy, leafToSpineCableOccupancy)
    # this means that
    #   - the highest priority will be to balance the spine switch occupancy,
    #   - then the leaf to spine cable occupancy
    #   - and then the spine to leaf cable occupancy

    return (occupancyTable.getSpineSwitchOccupancy(route),
            occupancyTable.getLeafToSpineCableOccupancy(route),
            occupancyTable.getSpineToLeafCableOccupancy(route))

#----------------------------------------------------------------------


def makeRouteRankingFunction(routingAlgoObj):
    return routeRanking01

    
