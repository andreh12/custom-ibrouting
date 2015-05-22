#!/usr/bin/env python

# tool to parse generate our custom Infiniband routing table

import sys, os, commands

try:
    import pylab
    havePylab = True
except ImportError:
    havePylab = False

from pprint import pprint

sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network/"))

import iblinkStatusUtils 
import utils

#----------------------------------------------------------------------
iblinkInfoExe = "/usr/sbin/iblinkinfo"

# from ~/2012-06-infiniband/config-cdaq-2015-04-02.py
# (44x44)
# sourceHosts = ['ru-c2e13-22-01', 'ru-c2e13-23-01', 'ru-c2e15-19-01', 'ru-c2e12-16-01', 'ru-c2e12-17-01', 'ru-c2e12-18-01', 'ru-c2e13-27-01', 'ru-c2e13-28-01', 'ru-c2e13-29-01', 'ru-c2e15-27-01', 'ru-c2e12-10-01', 'ru-c2e12-11-01', 'ru-c2e12-12-01', 'ru-c2e12-27-01', 'ru-c2e12-28-01', 'ru-c2e12-29-01', 'ru-c2e14-27-01', 'ru-c2e12-13-01', 'ru-c2e12-14-01', 'ru-c2e12-15-01', 'ru-c2e12-24-01', 'ru-c2e12-25-01', 'ru-c2e12-26-01', 'ru-c2e13-16-01', 'ru-c2e13-17-01', 'ru-c2e13-18-01', 'ru-c2e15-16-01', 'ru-c2e13-10-01', 'ru-c2e13-11-01', 'ru-c2e13-12-01', 'ru-c2e13-13-01', 'ru-c2e13-14-01', 'ru-c2e13-15-01', 'ru-c2e15-13-01', 'ru-c2e12-19-01', 'ru-c2e13-24-01', 'ru-c2e13-30-01', 'ru-c2e13-34-01', 'ru-c2e15-30-01', 'ru-c2e15-34-01', 'ru-c2e15-35-01', 'ru-c2e12-30-01', 'ru-c2e12-35-01', 'ru-c2e14-30-01']

# destHosts = ['bu-c2f16-35-01', 'bu-c2e18-35-01', 'bu-c2d33-30-01', 'bu-c2d41-30-01', 'bu-c2d42-30-01', 'bu-c2f16-31-01', 'bu-c2e18-31-01', 'bu-c2d33-20-01', 'bu-c2d41-20-01', 'bu-c2d35-30-01', 'bu-c2f16-11-01', 'bu-c2e18-11-01', 'bu-c2d31-20-01', 'bu-c2d36-20-01', 'bu-c2e18-23-01', 'bu-c2e18-25-01', 'bu-c2f13-29-01', 'bu-c2f16-13-01', 'bu-c2e18-13-01', 'bu-c2d31-30-01', 'bu-c2d36-30-01', 'bu-c2d34-10-01', 'bu-c2d34-20-01', 'bu-c2f16-17-01', 'bu-c2e18-17-01', 'bu-c2d32-10-01', 'bu-c2d37-10-01', 'bu-c2d38-10-01', 'bu-c2d38-20-01', 'bu-c2f16-37-01', 'bu-c2e18-39-01', 'bu-c2d35-20-01', 'bu-c2d42-20-01', 'bu-c2f16-29-01', 'bu-c2e18-29-01', 'bu-c2d33-10-01', 'bu-c2d41-10-01', 'bu-c2e18-41-01', 'bu-c2e18-43-01', 'bu-c2f16-09-01', 'bu-c2e18-09-01', 'bu-c2d31-10-01', 'bu-c2d36-10-01', 'bu-c2f16-23-01']

# 2015-05-12 22x22 from /nfshome0/mommsen/daq2Test/cdaq/canon_1str_22x22/daq2Symbolmap.txt

# sourceHosts = ["ru-c2e13-22-01", "ru-c2e13-23-01", "ru-c2e15-19-01", "ru-c2e12-16-01", "ru-c2e12-17-01", "ru-c2e12-18-01", "ru-c2e13-27-01", "ru-c2e13-28-01", "ru-c2e13-29-01", "ru-c2e15-27-01", "ru-c2e12-10-01", "ru-c2e12-11-01", "ru-c2e12-12-01", "ru-c2e12-27-01", "ru-c2e12-28-01", "ru-c2e12-29-01", "ru-c2e14-27-01", "ru-c2e12-13-01", "ru-c2e12-14-01", "ru-c2e12-15-01", "ru-c2e12-24-01", "ru-c2e12-25-01"]

# destHosts = [ "bu-c2f16-17-01", # "bu-c2f16-35-01",
#               "bu-c2e18-35-01", "bu-c2d33-30-01", "bu-c2d41-30-01", "bu-c2d42-30-01",
#               "bu-c2f16-09-01", # "bu-c2f16-31-01",
#               "bu-c2e18-31-01", "bu-c2d33-20-01", "bu-c2d41-20-01", "bu-c2d35-30-01", "bu-c2f16-11-01", "bu-c2e18-11-01", "bu-c2d31-20-01", "bu-c2d36-20-01", "bu-c2e18-23-01", "bu-c2e18-25-01", "bu-c2f13-29-01", "bu-c2f16-13-01", "bu-c2e18-13-01", "bu-c2d31-30-01", "bu-c2d36-30-01", "bu-c2d34-10-01"]


#----------------------------------------------------------------------

# from Route import Route

from RoutingAlgo import RoutingAlgo

#----------------------------------------------------------------------



#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------
from optparse import OptionParser
parser = OptionParser("""

    usage: %prog [options] 

    produces tailored Infiniband routing tables
    """
    )

parser.add_option("--srcfile",
                  default = None,
                  type="str",
                  help="name of a file with list of source hosts",
                  metavar="src.txt")

parser.add_option("--destfile",
                  default = None,
                  type="str",
                  help="name of a file with list of destination hosts",
                  metavar="src.txt")

parser.add_option("--iblinkfile",
                  default = None,
                  type="str",
                  help="name of a file with the output of iblinkinfo",
                  metavar="src.txt")

parser.add_option("--gvout",
                  default = None,
                  type="str",
                  help="name of graphviz output file",
                  metavar="out.gv")

parser.add_option("--algo",
                  default = None,
                  type="str",
                  help="name of a python file containing the functions needed by the routing algorithm",
                  metavar="algo.py")

(options, ARGV) = parser.parse_args()


if options.iblinkfile != None:
    # read the output of iblinkinfo from the given file
    linkData = iblinkStatusUtils.IBlinkStatusData(open(options.iblinkfile).read())
else:
    # run iblinkinfo ourselves
    if not os.path.exists(iblinkInfoExe):
        print "this host does not have " + iblinkInfoExe + ". Are you running on a host connected to the Infiniband network ?"
        sys.exit(1)

    linkData = iblinkStatusUtils.IBlinkStatusData(commands.getoutput("/usr/bin/sudo " + iblinkInfoExe))

if options.srcfile == None:
    print >> sys.stderr,"must specify a list of source hosts"
    sys.exit(1)
else:
    sourceHosts = utils.readHostsFile(options.srcfile)


if options.destfile == None:
    print >> sys.stderr,"must specify a list of destination hosts"
    sys.exit(1)
else:
    destHosts = utils.readHostsFile(options.destfile)
    

if not sourceHosts:
    print >> sys.stderr,"list of source hosts is empty"
    sys.exit(1)

if not destHosts:
    print >> sys.stderr,"list of destination hosts is empty"
    sys.exit(1)

#----------
# load the routing algorithm functions
#----------

if options.algo == None:
    print >> sys.stderr,"must specify a routing algorithm functions file"
    sys.exit(1)

import imp
RoutingAlgoRankingFunctions = imp.load_source("RoutingAlgoRankingFunctions",
                                              options.algo)


#----------------------------------------

# convert host names to LIDs
sourceLids = [ linkData.getLidFromHostname(host) for host in sourceHosts ]
destLids   = [ linkData.getLidFromHostname(host) for host in destHosts   ]


# if True:
#     routingAlgo = RoutingAlgo(linkData, sourceLids, destLids, routeRanking01)

routingAlgo = RoutingAlgo(linkData, sourceLids, destLids, None)
routingAlgo.routeRankingFunc = RoutingAlgoRankingFunctions.makeRouteRankingFunction(routingAlgo)

routingAlgo.run()

print "--------------------------------------"
print "summary of priority routes (RU to BU):"
print "--------------------------------------"

routingAlgo.occupancyTableMainRoutes.printSummary(showPlots = havePylab)
# routingAlgo.occupancyTable.printSummary()

# print a Graphviz file with the route occupancies
if options.gvout != None:
    fout = open(options.gvout,"w")
    fout.write(routingAlgo.graphVizText)
    fout.close()

if havePylab:
    pylab.show()

# sys.exit(1)




# TEST
if False:
    routes = fabricTable.makeRoutes(sourceLids[0], destLids[0])
    pprint(routes)
    print len(routes)



fout = open("/tmp/routing-table-%dx%d.txt" % (len(sourceHosts), len(destHosts)), "w")
routingAlgo.fabricTable.doPrint(fout)
fout.close()
#----------------------------------------
