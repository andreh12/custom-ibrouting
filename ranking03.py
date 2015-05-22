#!/usr/bin/env python


#----------------------------------------------------------------------
def routeRanking03(occupancyTable, route, sourceLid, destLid):

    # balance the cable occupancies

    oc1  = occupancyTable.getSpineSwitchOccupancy(route)
    oc2 = occupancyTable.getLeafToSpineCableOccupancy(route)
    oc3 = occupancyTable.getSpineToLeafCableOccupancy(route)

    return (
        max(oc2, oc3),
        oc1,
        oc2,
        oc3
        )

#----------------------------------------------------------------------


def makeRouteRankingFunction(routingAlgoObj):
    return routeRanking03

    
