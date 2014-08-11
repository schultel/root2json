#
# Simple converter to get ROOT histograms into JSON format used in PaPA/PISA
#
# Sebastian Boeser <sboeser@physik.uni-bonn.de>
#

import sys
import ROOT
import numpy
import logging
from array import array
from argparse import ArgumentParser

try:
    import simplejson as json
except ImportError:
    import json


def find_hist(obj, histkey=None, histlist={}):
    '''Iteratively loop over a nested json object and'''
    '''find a dicts that match our histogram definition'''

    def is_hist(obj):
        if not type(obj)==dict:
            return False
        if not sorted(obj.keys())==['czbins','ebins','map']:
            return False
        return True

    #Check if what we have is a histogram
    if is_hist(obj):
        logging.debug("Found histogram %s"%histkey)
        #append with current key
        histlist[histkey]=obj
        return histlist

    #Check if we have something iterable
    if not type(obj) in [dict,list]:
        return histlist

    #Check that there is something to loop over
    if not len(obj):
        return histlist

    #Get a list of keys and values
    if type(obj) == dict:
        keys, values = zip(*obj.items())
    if type(obj) == list:
        keys, values = [str(x) for x in range(len(obj))],obj

    #Loop over elements and check if they are hists
    for key, value in zip(keys,values):
        newkey = (histkey + '_' if histkey else '') + key
        find_hist(value,histkey=newkey,histlist=histlist)
    
    return histlist

def is_logarithmic(edges, maxdev = 1e-5):
    '''Check whether the bin edges correspond to a logarithmic axis'''
    if numpy.any(numpy.array(edges) < 0): return False
    logedges = numpy.logspace(numpy.log10(edges[0]),numpy.log10(edges[-1]),len(edges))
    return numpy.abs(edges-logedges).max() < maxdev 


def json2root(infile):
     
    data = json.load(open(infile))
    hists = find_hist(data)

    logging.info("Found %u histograms"%len(hists))

    rhists=[]
    #Loop over histograms
    for key,hist in hists.iteritems():

        etitle='E/GeV'
        cztitle='cos(#theta)'

        #Check if our bins have a logarithmic spacing
        if is_logarithmic(hist['ebins']):
            logging.debug('Converting energy axis to log10(E)')
            #Convert to linear binning in logE
            hist['ebins']=numpy.log10(hist['ebins'])
            etitle = 'log_{10}(E/GeV)'

        #New 2D histogram
        rhist = ROOT.TH2F(key,key,
                          len(hist['ebins'])-1,array('f',hist['ebins']),
                          len(hist['czbins'])-1,array('f',hist['czbins']))

        #Fill in the histrogram
        for (ie,icz),val in numpy.ndenumerate(hist['map']):
            rhist.SetBinContent(ie+1,icz+1,val)

        #Set nice labels and cosmetics
        rhist.GetXaxis().SetTitle(etitle)
        rhist.GetYaxis().SetTitle(cztitle)
        rhist.SetStats(False)

        for ax in [rhist.GetXaxis(),rhist.GetYaxis()]:
            ax.SetLabelSize(0.04)
            ax.SetTitleSize(0.04)

        rhists += [rhist]

    return rhists


if __name__ == '__main__':

   # parser
    parser = ArgumentParser(description='Simple converter to convert JSON'
              'maps as used in PaPA/PISA into ROOT histograms')

    parser.add_argument('infile', metavar='JSONFILE', type=str, nargs=1)
    
    parser.add_argument('-o', '--outfile', dest='outfile', metavar='ROOTFILE', type=str, action='store',
                        help='file to store the output', default='out.root')
    
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='set verbosity level')
    
    args = parser.parse_args()

    #Set verbosity level
    levels = {0:logging.WARN,
          1:logging.INFO,
          2:logging.DEBUG}
    logging.basicConfig(format='[%(levelname)8s] %(message)s')
    logging.root.setLevel(levels[min(2,args.verbose)])

    histlist = json2root(args.infile[0])
 
    #Write out stuff in ROOT file
    outfile = ROOT.TFile(args.outfile,'RECREATE')
    if outfile.IsZombie():
        logging.error('Failed to open ROOT file %s'%outfile)
        sys.exit(1)

    for rhist in histlist:
        rhist.Write()
    
    outfile.Close()

    #Delete histograms explicity to kill it on ROOT/C++ side
    for rhist in histlist:
        rhist.Delete()


        







