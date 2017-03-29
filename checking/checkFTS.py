#!/usr/bin/env python

import sys, gzip, re, os

sys.path.append(os.path.expanduser("~aholz/DAQTools/Diagnostics/trunk/network"))
from iblinkInfoUtils import IBlinkStatusData

# performs some checks on the output of dumpfts

from MultiFTStable import MultiFTStable

#----------------------------------------------------------------------

def checkMissingEntries(ftsTable, linkData, showDeviceNames):
    # look for missing entries, i.e. check if all routing tables have entries for all LIDs

    allLIDs = sorted(linkData.allLIDs)

    pcLids = ftsTable.getPcLids()

    for switchLid, switchTable in ftsTable.routingTables.items():
        # for lid in ftsTable.getAllLids():
        for lid in allLIDs:
            if not switchTable.destLidToPort.has_key(lid):
                if lid in pcLids:
                    typeName = "pc"
                elif lid in ftsTable.switchLids:
                    typeName = 'switch'
                else:
                    assert False

                if showDeviceNames:
                    print "switch %d (%s) does not have an entry for %s lid %d (%s)" % (switchLid, 
                                                                                        linkData.getDeviceName(switchLid),
                                                                                        typeName, lid, linkData.getDeviceName(lid))
                else:
                    print "switch %d does not have an entry for %s lid %d" % (switchLid, 
                                                                              typeName, lid)
                    


#----------------------------------------------------------------------


def checkConnectivitySinglePair(srcLid, destLid, pcLids, showDeviceNames):
    # note that we need to rerun/reset this for every destination
    # again

    maxPathLength = 10

    # if the source is a PC, we first go to the switch
    if srcLid in pcLids:
        switchPortData = ftsTable.getSwitchPortFromPClid(srcLid)

        # go to the switch
        currentSwitchLid = switchPortData['switchLid']

    else:
        # we start from a switch
        currentSwitchLid = srcLid

    #----------

    switchLidsSeen = [ ]

    pathLength = 0

    while pathLength < maxPathLength:

        # get the routing table of the switch
        routingTable = ftsTable.routingTables[currentSwitchLid]

        switchLidsSeen.append(currentSwitchLid)

        # check if the destination is connected to this switch
        if ftsTable.getSwitchPortFromPClid(destLid)['switchLid'] == currentSwitchLid:
            # yes, we've found the destination
            # TODO: check again that it points to the 
            #       right output port
            break

        if currentSwitchLid == destLid:
            # we've found a destination switch
            break

        # we must go over another switch
        # we must know which switch LID is connected to the output port
        # to get the next routing table
        # 
        # however we can't know what is at the other end
        # of the cable without iblinkinfo data
        outputPort = routingTable.getOutputPort(destLid)

        if outputPort is None:
            print "NOT OK from %d to %d" % (srcLid, destLid), ": no output port found for dest LID %d on switch LID %d" % (
                destLid, currentSwitchLid)
            return


        peerSwitchData = linkData.getSwitchPortData(currentSwitchLid, outputPort)

        peerLid = peerSwitchData['peerLid']

        # prepare next iteration
        currentSwitchLid = peerLid

        pathLength += 1


    if not showDeviceNames:
        switchLidsDesc = switchLidsSeen
    else:
        switchLidsDesc = [ "%d (%s)" % (lid, linkData.getDeviceName(lid)) for lid in switchLidsSeen ]

    if pathLength >= maxPathLength:
        print "loop detected from %d to %d" % (srcLid, destLid),switchLidsDesc
    else:
        print "ok from %d to %d" % (srcLid, destLid), switchLidsDesc
    


#----------------------------------------------------------------------

def checkConnectivity(ftsTable, linkData, showDeviceNames):
    # check that from each lid we can reach each other lid

    allLids = ftsTable.getAllLids()

    pcLids = ftsTable.getPcLids()

    for srcLid in sorted(allLids):
        # for the moment, do not test switch to switch connections
        # if srcLid in ftsTable.switchLids:
        #    continue

        for destLid in allLids:
            checkConnectivitySinglePair(srcLid, destLid, pcLids, showDeviceNames)
            



#----------------------------------------------------------------------
# main
#----------------------------------------------------------------------

if __name__ == '__main__':

    from optparse import OptionParser
    parser = OptionParser("""

        usage: %prog [options] fts-table-file iblinkinfo-output-file

        performs some checks on Infiniband routing tables
        """
        )

    parser.add_option("--device-names",
                      default = False,
                      dest = "showDeviceNames",
                      action = "store_true",
                      help="print device names instead of just LIDs",
                      )
    (options, ARGV) = parser.parse_args()

    assert len(ARGV) == 2

    fname = ARGV.pop(0)

    if fname.endswith(".gz"):
        fin = gzip.open(fname)
    else:
        fin = open(fname)


    ftsTable = MultiFTStable(fin)

    #----------
    iblinkStatusfile = ARGV.pop(0)

    linkData = IBlinkStatusData.fromIBlinkInfoOutput(open(iblinkStatusfile).read())

    #----------
    # perform checks
    #----------

    checkMissingEntries(ftsTable, linkData, options.showDeviceNames)

    # check that we can reach lid from each other lid
    checkConnectivity(ftsTable, linkData, options.showDeviceNames)


    if False:
        #----------
        # find ports where switches are connected to switches
        #
        # assume ports for which there is more than one destination LID
        # are connected to another switch and those on which
        # only one destination LID is found are PCs (this may actually
        # also happen for a switch which has only one port connected...)
        #----------
        pass

    #----------
    # find to which switch each PC is connected to: look at 
    # those switch ports to which only one destination LID
    # is assigned
    #----------


