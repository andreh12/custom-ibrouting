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

    def makeSummaryData(self):
        retval = []


        retval.append(dict(title = "spine switch occupancies",
                           counts = self.spineSwitchLIDtoNumRoutes.getOccupancyHistogram(reverse = True),
                           itemTemplate = "${numItems} switches have ${occupancy} paths",

                           # plotting parameters
                           xlabel = "number of routes",
                           ylabel = "number of switches",
                           plotTitle = 'routes per spine switch'
                           ))

        retval.append(dict(title = "spine to leaf cable occupancies",
                           counts = self.spineSwitchLIDandPortToNumRoutes.getOccupancyHistogram(reverse = True),
                           itemTemplate = "${numItems} cables have ${occupancy} paths",

                           # plotting parameters
                           xlabel = "number of routes",
                           ylabel = "number of cables",
                           plotTitle = 'routes per spine to leaf cable',

                           ))

        retval.append(dict(title = "leaf to spine cable occupancies",
                           counts = self.inputLeafSwitchLIDandPortToNumRoutes.getOccupancyHistogram(reverse = True),
                           itemTemplate = "${numItems} cables have ${occupancy} paths",

                           # plotting parameters
                           xlabel = "number of routes",
                           ylabel = "number of cables",
                           plotTitle = 'routes per leaf to spine cable',

                           ))

        
        return retval


    #----------------------------------------        

    def printSummary(self, data, os = sys.stdout):

        for index, line in enumerate(data):

            if index > 0:
                print >> os

            # print the title
            print >> os, line['title'] + ":"

            import string
            templ = string.Template(line['itemTemplate'])

            for occupancy, numItems in line['counts']:
                print >> os, "  " + templ.substitute(dict(numItems  = "%4d" % numItems,
                                                          occupancy = "%4d" % occupancy))

            #----------


    #----------------------------------------

    def printSummaryHTML(self, data, os):

        # produces a HTML table with the summary
        # (does not produce a full html document, i.e.
        # no headers and footers etc.)

        for index, line in enumerate(data):

            if index > 0:
                print >> os, "<hr/>"

            print >> os,"<div>"
            # print the title
            print >> os, line['title'] + ":" + "<br/>"

            import string
            templ = string.Template(line['itemTemplate'])

            print >> os,'<table border="1">'

            # table header
            print >> os,"<tr>"
            print >> os,"<th>num cables/switches</th>"
            print >> os,"<th>occupancy per cable/switch</th>"
            
            print >> os,"</tr>"

            for occupancy, numItems in line['counts']:
                print >> os,"<tr>"
                print >> os,"<td>%d</td>" % numItems
                print >> os,"<td>%d</td>" % occupancy
                print >> os,"</tr>"

            print >> os,"</table>"
            print >> os,"</div>"


    #----------------------------------------

    def makeOccupancyPlots(self, data, interactive):
        # produces files, does not show them on screen
        # @return the names of the temporary files generated

        retval = []

        import pylab

        for line in data:

            # collect the values 
            xvalues = []; yvalues = []

            for occupancy, numItems in line['counts']:
                xvalues.append(occupancy); yvalues.append(numItems)
        
            fig = pylab.figure(facecolor = 'white')
            pylab.bar(xvalues, yvalues, align = 'center')
            pylab.title(line['plotTitle'])
            pylab.grid()
            pylab.xlabel(line['xlabel'])
            pylab.ylabel(line['ylabel'])

            # save the figure
            import tempfile
            fout = tempfile.NamedTemporaryFile(suffix = ".png")


            if not interactive:
                pylab.savefig(fout.name)
                fig.close()

            # make sure the return the file object,
            # so that it does not get deleted too early
            # in python 2.4
            retval.append(fout)

        if not interactive:
            return retval
        

    #----------------------------------------
