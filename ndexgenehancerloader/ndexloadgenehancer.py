#! /usr/bin/env python

import argparse
import sys
import logging
import os
import csv
from logging import config
from ndexutil.config import NDExUtilConfig
import ndex2
from ndex2.client import Ndex2
import ndexgenehancerloader

import re

logger = logging.getLogger(__name__)
from datetime import datetime

TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'
import json
import pandas as pd
import ndexutil.tsv.tsv2nicecx2 as t2n

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"

DATA_DIR = 'genehancer_files'
LOAD_PLAN = 'loadplan.json'
GENEHANCER_URL = 'https://www.genecards.org/GeneHancer_version_4-4'

def _get_load_plan():
    return os.path.join(LOAD_PLAN)

def _parse_arguments(desc, args):
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    helpFormatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=helpFormatter)
    parser.add_argument('datadir', help='Directory that GeneHancer data is downloaded to and processed from')
    parser.add_argument('--profile', help='Profile in configuration '
                                          'file to use to load '
                                          'NDEx credentials which means'
                                          'configuration under [XXX] will be'
                                          'used '
                                          '(default '
                                          'ndexgenehancerloader)',
                        default='ndexgenehancerloader')
    parser.add_argument('--logconf', default=None,
                        help='Path to python logging configuration file in '
                             'this format: https://docs.python.org/3/library/'
                             'logging.config.html#logging-config-fileformat '
                             'Setting this overrides -v parameter which uses '
                             ' default logger. (default None)')

    parser.add_argument('--conf', help='Configuration file to load '
                                       '(default ~/' +
                                       NDExUtilConfig.CONFIG_FILE)
    parser.add_argument('--verbose', '-v', action='count', default=0,
                        help='Increases verbosity of logger to standard '
                             'error for log messages in this module and'
                             'in ' + TSV2NICECXMODULE + '. Messages are '
                             'output at these python logging levels '
                             '-v = ERROR, -vv = WARNING, -vvv = INFO, '
                             '-vvvv = DEBUG, -vvvvv = NOTSET (default no '
                             'logging)')
    parser.add_argument('--version', action='version',
                        version=('%(prog)s ' +
                                 ndexgenehancerloader.__version__))
    parser.add_argument('--noheader', action='store_true', default=False,
                        help='If set, assumes there is no header in the data file and uses a default set of headers')
    parser.add_argument('--loadplan', help='Use alternate load plan file', default=_get_load_plan())

    return parser.parse_args(args)


def _setup_logging(args):
    """
    Sets up logging based on parsed command line arguments.
    If args.logconf is set use that configuration otherwise look
    at args.verbose and set logging for this module and the one
    in ndexutil specified by TSV2NICECXMODULE constant
    :param args: parsed command line arguments from argparse
    :raises AttributeError: If args is None or args.logconf is None
    :return: None
    """

    if args.logconf is None:
        level = (50 - (10 * args.verbose))
        logging.basicConfig(format=LOG_FORMAT,
                            level=level)
        logging.getLogger(TSV2NICECXMODULE).setLevel(level)
        logger.setLevel(level)
        return

    # logconf was set use that file
    logging.config.fileConfig(args.logconf,
                              disable_existing_loggers=False)


class NDExGeneHancerLoader(object):
    """
    Class to load content
    """
    def __init__(self, args):
        """

        :param args:
        """
        self._conf_file = args.conf
        self._profile = args.profile
        self._user = None
        self._pass = None
        self._server = None

        self._datadir = os.path.abspath(args.datadir)
        self._local_file_name = os.path.join(self._datadir, 'genehancerData.xlsx')

        self._noheader = args.noheader
        self._loadplan = args.loadplan

        self._ndex = None
        self._network_summaries = None

    def _parse_config(self):
            """
            Parses config
            :return:
            """
            ncon = NDExUtilConfig(conf_file=self._conf_file)
            con = ncon.get_config()
            self._user = con.get(self._profile, NDExUtilConfig.USER)
            self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
            self._server = con.get(self._profile, NDExUtilConfig.SERVER)

    def _create_ndex_connection(self):
        """
        creates connection to ndex
        """
        if self._ndex is None:
            try:
                self._ndex = Ndex2(host=self._server, username=self._user, password=self._pass)
            except Exception as e:
                print(e)
                self._ndex = None
        return self._ndex

    def _load_network_summaries_for_user(self):
        """
        Gets a dictionary of all networks for user account
        <network name upper cased> => <NDEx UUID>
        :return: 0 if success, 2 otherwise
        """
        self._network_summaries = {}
        try:
            network_summaries = self._ndex.get_network_summaries_for_user(self._user)
        except Exception as e:
            print(e)
            return None, 2

        for summary in network_summaries:
            if summary.get('name') is not None:
                self._network_summaries[summary.get('name').upper()] = summary.get('externalId')

        return self._network_summaries, 0

    def _upload_CX(self, path_to_network_in_CX):
        network_name = self._get_network_name(path_to_network_in_CX)
        network_UUID = self._network_summaries.get(network_name.upper())

        with open(path_to_network_in_CX, 'rb') as network_out:
            try:
                if network_UUID is None:
                    print('\n{} - started uploading "{}" on {} for user {}...'
                        .format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        network_name, self._server, self._user))
                    self._ndex.save_cx_stream_as_new_network(network_out)
                    print('{} - finished uploading "{}" on {} for user {}'
                        .format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                        network_name, self._server, self._user))
                else :
                    print('\n{} - started updating "{}" on {} for user {}...'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), network_name,
                                 self._server, self._user))
                    self._ndex.update_cx_network(network_out, network_UUID)
                    print('{} - finished updating "{}" on {} for user {}'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), network_name,
                                 self._server, self._user))

            except Exception as e:
                print('{} - unable to update or upload "{}" on {} for user {}'.
                      format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), network_name,
                             self._server, self._user))
                print(e)
                return 2
        return 0    

    def _get_network_name(self, path_to_network_in_CX):
        split = path_to_network_in_CX.split("/")
        last = split[-1]
        name = last.split(".")[0]
        if name.startswith('result'):
            return name[len('result'):]
        return name

    def _check_if_data_dir_exists(self):
        data_dir_existed = True

        if not os.path.exists(self._datadir):
            data_dir_existed = False
            os.makedirs(self._datadir, mode=0o755)

        return data_dir_existed  


    def _get_default_header(self): 
        header = [
            'chrom',
            'source',
            'feature name',
            'start',
            'end',
            'score',
            'strand',
            'frame',
            'attributes'
        ]
        return header

    def _get_output_header(self):
        header = [
            "Enhancer",
            "Chromosome",
            "StartLocation",
            "EndLocation",
            "EnhancerConfidenceScore",
            "EnhancerType",
            "Gene",
            "GeneRep",
            "GeneEnhancerScore",
            "GeneType"
        ]
        return header

    def _process_data_file(self, filename):
        resultFilePath = self._datadir + "/result" + filename
        with open(self._datadir + "/" + filename, 'r') as readFile:
            reader = csv.reader(readFile, delimiter=',')
            with open(resultFilePath, 'w') as writeFile:
                writer = csv.writer(writeFile)
                writer.writerow(self._get_output_header())
                header = self._get_default_header()
                for i, line in enumerate(reader):
                    if (i == 0):
                        if (self._noheader is True):
                            header = line
                    else:
                        attributes = line[header.index('attributes')].split(";")
                        #Find enhancer attributes
                        enhancerId = attributes[0].split("=")[1]
                        enhancerChrom = line[header.index('chrom')]
                        enhancerStart = line[header.index('start')]
                        enhancerEnd = line[header.index('end')]
                        enhancerConfidenceScore = line[header.index('score')]
                        #Find genes
                        for i in range(1, len(attributes), 2):
                            geneName = attributes[i].split("=")[1]
                            if (re.match('^GC([0-9]{2}|MT)(P|M|U9)[A-Za-z]?[0-9]+$', geneName) or 
                                re.match('^LOC[0-9]+$', geneName)):
                                geneRep = "genecards:" + geneName
                            elif (re.match('^ENS[A-Za-z]+[0-9]+$', geneName)):
                                geneRep = "ensembl:" + geneName
                            elif (re.match('^[A-Z][A-Za-z0-9]+$', geneName)):
                                geneRep = "hgnc:" + geneName
                            else:
                                geneRep = geneName
                            geneEnhancerScore = attributes[i+1].split("=")[1]
                            writer.writerow([
                                enhancerId,
                                enhancerChrom,
                                enhancerStart,
                                enhancerEnd,
                                enhancerConfidenceScore,
                                "enhancer",
                                geneName,
                                geneRep,
                                geneEnhancerScore,
                                "protein"
                            ])
        return resultFilePath

    def _generate_nice_CX(self, filePath, originalName):
        cxFilePath = self._get_cx_file_path(filePath)
        loadPlan = self._loadplan
        with open(loadPlan, 'r') as lp:
            plan = json.load(lp)
        dataframe = pd.read_csv(filePath,
                                dtype=str,
                                na_filter=False,
                                delimiter=',',
                                engine='python')
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, plan)

        #Add network attributes
        network.set_name(originalName)
        network.set_network_attribute("description", "GeneHancer dataset " + originalName + "uploaded as a cytoscape network")
        network.set_network_attribute("reference", 'Fishilevich S, Nudel R, Rappaport N, et al. GeneHancer: genome-wide integration of enhancers and target genes in GeneCards. <em>Database (Oxford).</em> 2017;2017:bax028. <a href=http://doi.org/10.1093/database/bax028 target="_blank">doi:10.1093/database/bax028</a>')
        network.set_network_attribute("networkType", "[interactome, geneassociation]")
        network.set_network_attribute("__iconurl", "https://www.genecards.org/Images/Companions/Logo_GH.png")

        with open(cxFilePath, 'w') as f:
            json.dump(network.to_cx(), f, indent=4)
        return cxFilePath

    def _get_cx_file_path(self, filePath):
        reverseString = filePath[::-1]
        newString = reverseString.replace('vsc.', 'xc.', 1)
        return newString[::-1]

    def _get_original_name(self, fileName):
        reverseString = fileName[::-1]
        newString = reverseString.split(".", 1)[1]
        return newString[::-1]

    def run(self):
        """
        Runs content loading for NDEx GeneHancer Content Loader
        :param theargs:
        :return:
        """
        # Setup
        self._parse_config()

        # Check for data
        data_dir_existed = self._check_if_data_dir_exists()
        if data_dir_existed is False:
            print('Data directory does not exist')
            return 2

        #Connect to ndex
        self._create_ndex_connection()
        net_summaries, status_code = self._load_network_summaries_for_user()
        if status_code != 0:
            return status_code

        # Turn data into network
        for filename in os.listdir(self._datadir):
            if filename.startswith("result"):
                continue
            print('\n{} - started processing "{}"...'
                        .format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), filename))
            originalName = self._get_original_name(filename)
            resultFilePath = self._process_data_file(filename)
            cxFilePath = self._generate_nice_CX(resultFilePath, originalName)
            # Upload data
            self._upload_CX(cxFilePath)


        return 0          

def main(args):
    """
    Main entry point for program
    :param args:
    :return:
    """
    desc = """
    Version {version}

    Loads NDEx GeneHancer Content Loader data into NDEx (http://ndexbio.org).
    
    To connect to NDEx server a configuration file must be passed
    into --conf parameter. If --conf is unset the configuration 
    the path ~/{confname} is examined. 
         
    The configuration file should be formatted as follows:
         
    [<value in --profile (default ncipid)>]
         
    {user} = <NDEx username>
    {password} = <NDEx password>
    {server} = <NDEx server(omit http) ie public.ndexbio.org>
    
    
    """.format(confname=NDExUtilConfig.CONFIG_FILE,
               user=NDExUtilConfig.USER,
               password=NDExUtilConfig.PASSWORD,
               server=NDExUtilConfig.SERVER,
               version=ndexgenehancerloader.__version__)
    theargs = _parse_arguments(desc, args[1:])
    theargs.program = args[0]
    theargs.version = ndexgenehancerloader.__version__

    try:
        _setup_logging(theargs)
        loader = NDExGeneHancerLoader(theargs)
        return loader.run()
    except Exception as e:
        logger.exception('Caught exception')
        return 2
    finally:
        logging.shutdown()


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main(sys.argv))
