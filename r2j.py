#!/usr/bin/env python
#
# Simple converter to get ROOT histograms into JSON format used in PaPA/PISA
#
# Sebastian Boeser <sboeser@physik.uni-bonn.de>
# Lukas Schulte <lschulte@physik.uni-bonn.de>
#

import sys
import ROOT
import numpy
import logging
from argparse import ArgumentParser


def convert1Dhisto(hist):

    #Get the bin edges
    ebins = []
    axis = hist.GetXaxis()
    ebins += [axis.GetXmin()]
    for ibin in range(1,axis.GetNbins()+1):
        ebins += [axis.GetBinUpEdge(ibin)]

    #Convert to numpy arrays, energy in log10
    ebins = numpy.power(10,numpy.array(ebins))

    logging.debug('Found %u bins in energy from %.2f to %.2f'%
                   (len(ebins)-1, ebins[0], ebins[-1]))

    #Get the actual map
    dmap = numpy.zeros((len(ebins)-1))
    for ebin in range(1,len(ebins)):
        dmap[ebin-1]=hist.GetBinContent(ebin)

    #Compile in dict
    ret_dict = {'ebins': ebins,
                'entries': dmap }
    return ret_dict


def convert2Dhisto(hist):

    #Get the bin edges
    ebins = []
    czbins = []
    for edges, axis in [(ebins,hist.GetXaxis()),
                        (czbins,hist.GetYaxis())]:
        edges += [axis.GetXmin()]
        for ibin in range(1,axis.GetNbins()+1):
            edges += [axis.GetBinUpEdge(ibin)]


    #Convert to numpy arrays, energy in log10
    ebins = numpy.power(10,numpy.array(ebins))
    czbins = numpy.array(czbins)

    for edges, label in [(ebins,'energy'),(czbins,'cos(zenith)')]:
        logging.debug('Found %u bins in %s from %.2f to %.2f'%
                       (len(edges)-1,label,edges[0],edges[-1]))

    #Get the actual map
    dmap = numpy.zeros((len(ebins)-1,len(czbins)-1))
    for ebin in range(1,len(ebins)):
        for czbin in range(1,len(czbins)):
            dmap[ebin-1,czbin-1]=hist.GetBinContent(ebin,czbin)

    #Compile in dict
    ret_dict = {'ebins': ebins,
                'czbins': czbins,
                'map' : dmap }
    return ret_dict


def convert3Dhisto(hist):

    #Get the bin edges
    czbins_reco = []
    czbins_true = []
    ebins = []

    for edges, axis in [(czbins_reco, hist.GetXaxis()),
                        (czbins_true, hist.GetYaxis()),
                        (ebins, hist.GetZaxis())]:
        edges += [axis.GetXmin()]
        for ibin in range(1,axis.GetNbins()+1):
            edges += [axis.GetBinUpEdge(ibin)]


    #Convert to numpy arrays, energy in log10
    czbins_reco = numpy.array(czbins_reco)
    czbins_true = numpy.array(czbins_true)
    ebins = numpy.power(10,numpy.array(ebins))

    for edges, label in [(czbins_reco,'reco cos(zenith)'),
                          (czbins_true,'true cos(zenith)'),
                          (ebins,'energy')]:
        logging.debug('Found %u bins in %s from %.2f to %.2f'%
                       (len(edges)-1,label,edges[0],edges[-1]))

    #Get the actual map
    dmap = numpy.zeros((len(czbins_reco)-1, 
                        len(czbins_true)-1,
                        len(ebins)-1))
    for czb_re in range(1,len(czbins_reco)):
        for czb_tr in range(1,len(czbins_true)):
            for ebin in range(1,len(ebins)):
                dmap[czb_re-1,czb_tr-1,ebin-1]=hist.GetBinContent(czb_re,czb_tr,ebin)

    ret_dict = {'ebins': ebins,
                'czbins_true': czbins_true,
                'czbins_reco': czbins_reco,
                'map' : dmap }
    return ret_dict

def convertTFile(rfile):

    histlist = {}

    #Loop over the keys
    for key in rfile.GetListOfKeys():
        
        if key.GetClassName().startswith('TH1'):

            #Compile in dict and append
            logging.info('Converting 1D histrogram %s'%key.GetName())
            hist = rfile.Get(key.GetName())
            
            histlist[key.GetName()] = convert1Dhisto(hist)

        elif key.GetClassName().startswith('TH2'):

            #Compile in dict and append
            logging.info('Converting 2D histrogram %s'%key.GetName())
            hist = rfile.Get(key.GetName())
            
            histlist[key.GetName()] = convert2Dhisto(hist)

        elif key.GetClassName().startswith('TH3'):

            #Get the histogram
            logging.info('Converting 3D histrogram %s'%key.GetName())
            hist = rfile.Get(key.GetName())

            #Compile in dict and append
            histlist[hist.GetName()] = convert3Dhisto(hist)

        elif key.GetClassName() == 'TDirectoryFile':
            logging.info('Converting subdirectory %s'%key.GetName())
            subfile = rfile.Get(key.GetName())
            histlist[subfile.GetName()] = convertTFile(subfile)
            
        else:
            logging.debug('Skipping objekt %s which is of type %s'%
                           (key.GetName(),key.GetClassName()))
            continue

    logging.info("Converted %u histograms"%len(histlist))
    return histlist


def root2json(infile):

   #Open the ROOT file
    rfile = ROOT.TFile(infile)
    if rfile.IsZombie():
        logging.error('Failed to open ROOT file %s'%infile)
        sys.exit(1)

    return convertTFile(rfile)


def numpy2list(d):
    for key in d.keys():
        if isinstance(d[key], dict):
            numpy2list(d[key])
        elif isinstance(d[key], numpy.ndarray):
            d[key] = d[key].tolist()
        else:
            continue

try:
    import simplejson as json
except ImportError:
    import json

if __name__ == '__main__':

   # parser
    parser = ArgumentParser(description='Simple converter to get ROOT'
              'histograms into JSON format used in PaPA/PISA')

    parser.add_argument('infile', metavar='ROOTFILE', type=str, nargs=1)
    
    parser.add_argument('-o', '--outfile', dest='outfile', metavar='JSONFILE', type=str, action='store',
                        help='file to store the output', default='out.json')
    
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help='set verbosity level')
    
    args = parser.parse_args()

    #Set verbosity level
    levels = {0:logging.WARN,
          1:logging.INFO,
          2:logging.DEBUG}
    logging.basicConfig(format='[%(levelname)8s] %(message)s')
    logging.root.setLevel(levels[min(2,args.verbose)])

    #Convert all histos to ndarrays
    histlist = root2json(args.infile[0])
    
    #Convert all ndarrays to lists for json dumping
    numpy2list(histlist)
 
    #Write out stuff in JSON
    with open(args.outfile,'w') as ofile:
        json.dump(histlist,ofile)


        







