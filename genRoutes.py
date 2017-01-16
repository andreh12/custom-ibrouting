#!/usr/bin/env python

# tool to parse generate our custom Infiniband routing table

import sys, os, commands, time


from pprint import pprint

sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network/"))

import iblinkInfoUtils 
import utils

#----------------------------------------------------------------------
iblinkInfoExe = "/usr/sbin/iblinkinfo"


#----------------------------------------------------------------------

# from Route import Route

from RoutingAlgo import RoutingAlgo
# from RoutingAlgoPetr import RoutingAlgoPetr as RoutingAlgo

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

parser.add_option("--report",
                  default = None,
                  type="str",
                  help="name of output html file for route statistics report",
                  metavar="report.html")

parser.add_option("--algo",
                  default = None,
                  type="str",
                  help="name of a python file containing the functions needed by the routing algorithm",
                  metavar="algo.py")

parser.add_option("-o",
                  dest = "routingTableOutput",
                  default = None,
                  type="str",
                  help="name of the file where the routing tables should be written to. WARNING: This file is overwritten if it existing.",
                  metavar="table.txt")

parser.add_option("--noplots",
                  default = False,
                  action = "store_true",
                  help="disable plots"
                  )

(options, ARGV) = parser.parse_args()


if options.iblinkfile != None:
    # read the output of iblinkinfo from the given file
    linkData = iblinkInfoUtils.IBlinkStatusData(open(options.iblinkfile).read())
else:
    # run iblinkinfo ourselves
    if not os.path.exists(iblinkInfoExe):
        print "this host does not have " + iblinkInfoExe + ". Are you running on a host connected to the Infiniband network ?"
        sys.exit(1)

    linkData = iblinkInfoUtils.IBlinkStatusData(commands.getoutput("/usr/bin/sudo " + iblinkInfoExe))

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

# check that there are no overlaps between source
# and destination hosts
overlap = set(sourceHosts).intersection(destHosts)
if overlap:
    print >> sys.stderr,"found %d overlapping hosts between source and destination, exiting" % len(overlap)
    print >> sys.stderr,overlap
    sys.exit(1)

if not options.noplots:
    try:
        import pylab
        havePylab = True
    except ImportError:
        havePylab = False
else:
    havePylab = False

#----------
# load the routing algorithm functions
#----------

if options.algo == None:
    print >> sys.stderr,"must specify a routing algorithm functions file"
    sys.exit(1)

import imp
RoutingAlgoRankingFunctions = imp.load_source("RoutingAlgoRankingFunctions",
                                              options.algo)
#----------
# html report file
#----------
if options.report != None:
    htmlReportFile = open(options.report,"w")

    title = "routing table report %d x %d, %s" % (len(sourceHosts), len(destHosts), time.asctime())

    print >> htmlReportFile,"<html>"
    print >> htmlReportFile,"<head>"
    print >> htmlReportFile,"<title>%s</title>" % title
    print >> htmlReportFile,"</head>"
    print >> htmlReportFile,"<body>"

    print >> htmlReportFile,"<h1>%s</h1><br/><br/>" % title

    print >> htmlReportFile,"%d sources:<br/>" % len(sourceHosts),", ".join(sourceHosts) + "<br/><br/>"
    print >> htmlReportFile,"%d destinations:<br/>" % len(destHosts),", ".join(destHosts) + "<br/><br/>"
    
else:
    htmlReportFile = None

#----------------------------------------

# convert host names to LIDs
sourceLids = [ linkData.getLidFromHostname(host) for host in sourceHosts ]
destLids   = [ linkData.getLidFromHostname(host) for host in destHosts   ]

# make sure we have found the lids for all hosts
# (e.g. when the input file is in the wrong format, we will not find the LID here)
for lids, hosts in (
    (sourceLids, sourceHosts),
    (destLids, destHosts)):
    for lid, host in zip(lids, hosts):
        if lid == None:
            print >> sys.stderr,"could not find lid for host '%s'" % host
            sys.exit(1)


# if True:
#     routingAlgo = RoutingAlgo(linkData, sourceLids, destLids, routeRanking01)

routingAlgo = RoutingAlgo(linkData, sourceLids, destLids, None)
routingAlgo.routeRankingFunc = RoutingAlgoRankingFunctions.makeRouteRankingFunction(routingAlgo)

routingAlgo.run()

#----------
# print a Graphviz file with the route occupancies
#----------
if options.gvout != None:
    fout = open(options.gvout,"w")
    fout.write(routingAlgo.graphVizText)
    fout.close()


summaryData = routingAlgo.occupancyTableMainRoutes.makeSummaryData()

if htmlReportFile != None:
    routingAlgo.occupancyTableMainRoutes.printSummaryHTML(summaryData, htmlReportFile)

    if havePylab:
        # add the graphs
        images = routingAlgo.occupancyTableMainRoutes.makeOccupancyPlots(summaryData, False)

        # convert them to datauri objects
        for image in images:
            print >> htmlReportFile, "<hr/>"

            fin = open(image.name)
            data = fin.read()
            fin.close()

            data = data.encode("base64").replace("\n", "")

            print >> htmlReportFile,'<img src="data:image/png;base64,%s" /><br/>' % data
            

else:
    # print the summary on stdout
    print "--------------------------------------"
    print "summary of priority routes (RU to BU):"
    print "--------------------------------------"
    
    routingAlgo.occupancyTableMainRoutes.printSummary(summaryData)

    # show the plots
    if havePylab:
        routingAlgo.occupancyTableMainRoutes.makeOccupancyPlots(summaryData, True)
        pylab.show()


if htmlReportFile != None:
    print >> htmlReportFile,"</body>"
    htmlReportFile.close()

# TEST
if False:
    routes = fabricTable.makeRoutes(sourceLids[0], destLids[0])
    pprint(routes)
    print len(routes)


if options.routingTableOutput != None:
    fout = open(options.routingTableOutput,"w")
    routingAlgo.fabricTable.doPrint(fout)
    fout.close()

    print >> sys.stderr,"wrote routing table to",options.routingTableOutput

#----------------------------------------
