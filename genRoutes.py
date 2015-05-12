#!/usr/bin/env python

# tool to parse generate our custom Infiniband routing table

import sys, os, commands, pylab
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

# from Route import Route

from RoutingAlgo import RoutingAlgo

#----------------------------------------------------------------------


def routeRanking01(occupancyTable, route):

    # @return a tuple of (spineSwitchOccupancy, spineToLeafCableOccupancy, leafToSpineCableOccupancy)
    # this means that
    #   - the highest priority will be to balance the spine switch occupancy,
    #   - then the leaf to spine cable occupancy
    #   - and then the spine to leaf cable occupancy

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

print "--------------------------------------"
print "summary of priority routes (RU to BU):"
print "--------------------------------------"

routingAlgo.occupancyTableMainRoutes.printSummary()
# routingAlgo.occupancyTable.printSummary()

# print a Graphviz file with the route occupancies
fout = open("/tmp/t.gv","w")
fout.write(routingAlgo.graphVizText)
fout.close()

pylab.show()

# sys.exit(1)




# TEST
if False:
    routes = fabricTable.makeRoutes(sourceLids[0], destLids[0])
    pprint(routes)
    print len(routes)



routingAlgo.fabricTable.doPrint(sys.stdout)
#----------------------------------------
