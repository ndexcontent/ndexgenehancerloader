#! /usr/bin/env python

import argparse
import csv
from datetime import datetime
import json
import logging
from logging import config
import os
import pandas as pd
import re
import requests
import sys
import urllib
import xlrd

import ndex2
from ndex2.client import Ndex2
import ndexutil.tsv.tsv2nicecx2 as t2n
import ndexgenehancerloader
from ndexutil.config import NDExUtilConfig

logger = logging.getLogger(__name__)

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(fileName)s::%(funcName)s():%(lineno)d %(message)s"

TSV2NICECXMODULE = 'ndexutil.tsv.tsv2nicecx2'

DATA_DIR = 'genehancer_data'
"""
Default data directory
"""

LOAD_PLAN = 'loadplan.json'
"""
Default name of load plan file
"""

STYLE = 'style.cx'
"""
Default name of style file
"""

GENEHANCER_URL = 'https://www.genecards.org/GeneHancer_version_4-4'
"""
Url that data is downloaded from
"""

def get_package_dir():
    #print('get_package_dir')
    """
    Gets directory where package is installed
    :return:
    """
    return os.path.dirname(ndexgenehancerloader.__file__)

def _get_default_data_dir_name():
    #print('_get_default_data_dir_name')
    """
    Gets default data directory
    """
    return DATA_DIR

def _get_default_load_plan_name():
    #print('_get_default_load_plan_name')
    """
    Gets load plan stored with this package
    """
    return os.path.join(get_package_dir(), LOAD_PLAN)

def _get_default_style_name():
    #print('_get_default_style_name')
    """
    Gets style file stored with this package
    """
    return os.path.join(get_package_dir(), STYLE)

def _get_default_configuration_name():
    #print('_get_default_configuration_name')
    """
    Gets default configuration file
    """
    return os.path.join('~/', NDExUtilConfig.CONFIG_FILE)

def _parse_arguments(desc, args):
    #print('_parse_arguments')
    """
    Parses command line arguments
    :param desc:
    :param args:
    :return:
    """
    helpFormatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(description=desc,
                                     formatter_class=helpFormatter)
    parser.add_argument(
        '--datadir', 
        default=_get_default_data_dir_name(),
        help='Directory that GeneHancer data is found and processed in '
             '(default ' + DATA_DIR + ')')
    parser.add_argument(
        '--conf', 
        default=_get_default_configuration_name(),
        help='Configuration file to load (default ~/' 
             + NDExUtilConfig.CONFIG_FILE + ')')
    parser.add_argument(
        '--loadplan', 
        default=_get_default_load_plan_name(),
        help='Load plan file that should be used (default ' + LOAD_PLAN + ')')
    parser.add_argument(
        '--style', 
        default=_get_default_style_name(),
        help='Template network whose style should be used (default ' + STYLE + ')')
    parser.add_argument(
        '--profile', 
        default='ndexgenehancerloader',
        help='Profile in configuration file to use to load NDEx credentials ' 
             'which means configuration under [XXX] will be used '
             '(default ndexgenehancerloader)')
    parser.add_argument(
        '--logconf', 
        default=None,
        help='Path to python logging configuration file in this format: '
             'https://docs.python.org/3/library/logging.config.html#logging-config-fileformat '
             'Setting this overrides -v parameter which uses default logger. '
             '(default None)')
    parser.add_argument(
        '--verbose', 
        '-v', 
        action='count', 
        default=0,
        help='Increases verbosity of logger to standard error for log messages '
        'in this module and in ' + TSV2NICECXMODULE + '. Messages are output '
        'at these python logging levels -v = ERROR, -vv = WARNING, -vvv = INFO, '
        '-vvvv = DEBUG, -vvvvv = NOTSET (default no logging)')
    parser.add_argument(
        '--noheader', 
        action='store_true', 
        default=False,
        help='If set, assumes there is no header in the data file and uses a '
             'default set of headers')
    parser.add_argument(
        '--nocleanup', 
        action='store_true', 
        default=False,
        help='If set, intermediary files generated in the data director will '
             'not be removed')

    return parser.parse_args(args)


def _setup_logging(args):
    #print('_setup_logging')
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
        logging.basicConfig(format=LOG_FORMAT, level=level)
        logging.getLogger(TSV2NICECXMODULE).setLevel(level)
        logger.setLevel(level)
        return
    # logconf was set use that file
    logging.config.fileConfig(args.logconf, disable_existing_loggers=False)


class NDExGeneHancerLoader(object):
    """
    Class to load content
    """
    def __init__(self, args):
        #print('__init__')
        """

        :param args:
        """
        self._data_directory = os.path.abspath(args.datadir)
        self._conf_file = args.conf
        self._load_plan = args.loadplan
        self._style = args.style
        self._no_header = args.noheader
        self._no_cleanup = args.nocleanup

        self._profile = args.profile
        self._user = None
        self._pass = None
        self._server = None

        self._ndex = None
        self._network_summaries = None

    def _parse_config(self):
        #print('_parse_config')
        """
        Parses config
        :return:
        """
        ncon = NDExUtilConfig(conf_file=os.path.expanduser(self._conf_file))
        con = ncon.get_config()
        self._user = con.get(self._profile, NDExUtilConfig.USER)
        self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
        self._server = con.get(self._profile, NDExUtilConfig.SERVER)

    def _get_file_path(self, file_name):
        #print('_get_file_path')
        return self._data_directory + "/" + file_name

    def _get_load_plan(self):
        #print('_get_load_plan')
        with open(self._load_plan, 'r') as lp:
            plan = json.load(lp)
        return plan

    def _get_template_network(self):
        #print('_get_template_network')
        network = ndex2.create_nice_cx_from_file(os.path.abspath(self._style))
        return network

    def _get_original_name(self, file_name):
        #print('_get_original_name')
        reverse_string = file_name[::-1]
        new_string = reverse_string.split(".", 1)[1]
        return new_string[::-1]

    def _get_default_header(self): 
        #print('_get_default_header')
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
        #print('_get_output_header')
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

    def _data_directory_exists(self):
        #print('_data_directory_exists')
        return os.path.exists(self._data_directory)

    def _file_is_xl(self, file_name):
        #print('_file_is_xl')
        reverse_string = file_name[::-1]
        index = reverse_string.find('.')
        if reverse_string[index-2 : index] == 'lx':
            return True
        return False

    def _convert_from_xl_to_csv(self, file_path, original_name):
        #print('_convert_from_xl_to_csv')
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)

        new_csv_file_path = self._get_file_path("_intermediate" + original_name + ".csv")
        new_csv_file = open(new_csv_file_path, 'w')
        wr = csv.writer(new_csv_file, quoting=csv.QUOTE_ALL)

        for row_num in range(sheet.nrows):
            wr.writerow(sheet.row_values(row_num))

        new_csv_file.close()
        return new_csv_file_path

    def _create_ndex_connection(self):
        #print('_create_ndex_connection')
        """
        creates connection to ndex
        """
        if self._ndex is None:
            try:
                self._ndex = Ndex2(host=self._server, 
                                   username=self._user, 
                                   password=self._pass)
            except Exception as e:
                print(e)
                self._ndex = None
        return self._ndex

    def _load_network_summaries_for_user(self):
        #print('_load_network_summaries_for_user')
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
            return 2

        for summary in network_summaries:
            if summary.get('name') is not None:
                self._network_summaries[summary.get('name').upper()] = summary.get('externalId')

        return 0

    def _reformat_csv_file(self, csv_file_path, original_name):
        #print('_reformat_csv_file')
        result_csv_file_path = self._get_file_path("_result" + original_name + ".csv")

        with open(csv_file_path, 'r') as read_file:
            reader = csv.reader(read_file, delimiter=',')
            with open(result_csv_file_path, 'w') as write_file:
                writer = csv.writer(write_file)
                writer.writerow(self._get_output_header())

                for i, line in enumerate(reader):
                    if (i == 0):
                        if (self._no_header is True):
                            header = line
                        else:
                            header = self._get_default_header()
                    else:
                        attributes = line[header.index('attributes')].split(";")
                        #Find enhancer attributes
                        enhancer_id = attributes[0].split("=")[1]
                        enhancer_chrom = line[header.index('chrom')]
                        enhancer_start = line[header.index('start')]
                        enhancer_end = line[header.index('end')]
                        enhancer_confidence_score = line[header.index('score')]
                        
                        #Take care of trailing semi-colons
                        if len(attributes) % 2 == 0:
                            iRange = len(attributes) - 1
                        else:
                            iRange = len(attributes)

                        #Find genes
                        for i in range(1, iRange, 2):
                            gene_name = attributes[i].split("=")[1]
                            if (re.match('^GC([0-9]{2}|MT)(P|M|U9)[A-Za-z]?[0-9]+$', gene_name) or 
                                re.match('^LOC[0-9]+$', gene_name)):
                                gene_rep = "genecards:" + gene_name
                            elif (re.match('^ENS[A-Za-z]+[0-9]+$', gene_name)):
                                gene_rep = "ensembl:" + gene_name
                            elif (re.match('^[A-Z][A-Za-z0-9-]*$', gene_name)):
                                gene_rep = "hgnc:" + gene_name
                            else:
                                gene_rep = gene_name
                            gene_enhancer_score = attributes[i+1].split("=")[1]
                            writer.writerow([
                                enhancer_id,
                                enhancer_chrom,
                                enhancer_start,
                                enhancer_end,
                                enhancer_confidence_score,
                                "enhancer",
                                gene_name,
                                gene_rep,
                                gene_enhancer_score,
                                "gene"
                            ])
        return result_csv_file_path

    def _generate_nice_CX_from_csv(self, csv_file_path, load_plan):
        #print('_generate_nice_CX')
        dataframe = pd.read_csv(csv_file_path,
                                dtype=str,
                                na_filter=False,
                                delimiter=',',
                                engine='python')
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, load_plan)
        return network

    def _add_network_attributes(self, network, original_name):
        #print('_add_network_attributes')
        network.set_name(original_name)
        network.set_network_attribute(
            "description", 
            "GeneHancer dataset " + original_name + " uploaded as a cytoscape network")
        network.set_network_attribute(
            "reference", 
            'Fishilevich S, Nudel R, Rappaport N, et al. GeneHancer: '
            'genome-wide integration of enhancers and target genes in GeneCards. '
            '<em>Database (Oxford).</em> 2017;2017:bax028. '
            '<a href=http://doi.org/10.1093/database/bax028 '
            'target="_blank">doi:10.1093/database/bax028</a>')
        network.set_network_attribute(
            "networkType", 
            "[interactome, geneassociation]")
        network.set_network_attribute(
            "__iconurl", 
            "https://www.genecards.org/Images/Companions/Logo_GH.png")

    def _add_network_style(self, network, template_network):
        #print('_add_network_style')
        network.apply_style_from_network(template_network)
        
    def _write_cx_to_file(self, network, original_name):
        #print('_write_cx_to_file')
        cx_file_path = self._get_file_path("_result" + original_name + ".cx")
        with open(cx_file_path, 'w') as f:
            json.dump(network.to_cx(), f, indent=4)
        return cx_file_path

    def _upload_cx(self, cx_file_path, original_name):
        network_UUID = self._network_summaries.get(original_name.upper())
        with open(cx_file_path, 'rb') as network_out:
            try:
                if network_UUID is None:
                    print('\n{} - started uploading "{}" on {} for user {}...'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                 original_name, 
                                 self._server, 
                                 self._user))
                    self._ndex.save_cx_stream_as_new_network(network_out)
                    print('{} - finished uploading "{}" on {} for user {}'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                 original_name, 
                                 self._server, 
                                 self._user))
                else :
                    print('\n{} - started updating "{}" on {} for user {}...'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                 original_name,
                                 self._server, 
                                 self._user))
                    self._ndex.update_cx_network(network_out, network_UUID)
                    print('{} - finished updating "{}" on {} for user {}'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                 original_name,
                                 self._server, 
                                 self._user))

            except Exception as e:
                print('{} - unable to update or upload "{}" on {} for user {}'.
                      format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                             original_name,
                             self._server, 
                             self._user))
                print(e)
                return 2
        return 0 

    def run(self):
        #print('run')
        """
        Runs content loading for NDEx GeneHancer Content Loader
        :param theargs:
        :return:
        """
        # Setup
        self._parse_config()

        # Check for data
        data_dir_exists = self._data_directory_exists()
        if data_dir_exists is False:
            print('Data directory does not exist')
            return 2

        #Connect to ndex
        self._create_ndex_connection()
        status_code = self._load_network_summaries_for_user()
        if status_code != 0:
            return status_code

        # Turn data into network
        if len(os.listdir(self._data_directory)) == 0:
            print("No files found in directory: {}".format(self._data_directory))
            return 2

        else:
            for file_name in os.listdir(self._data_directory):
                # Skip files that result from this process
                if (file_name.startswith("_result") or 
                    file_name.startswith("_intermediate")):
                    continue

                print('\n{} - started processing "{}"...'.
                      format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                             file_name))
                original_name = self._get_original_name(file_name)
                
                # Check if file conversion is necessary
                file_is_xl = self._file_is_xl(file_name)
                if file_is_xl:
                    xl_file_path = self._get_file_path(file_name)
                    csv_file_path = self._convert_from_xl_to_csv(xl_file_path, 
                                                                 original_name)
                else:
                    csv_file_path = self._get_file_path(file_name)
                
                # Reformat csv into network
                result_csv_file_path = self._reformat_csv_file(csv_file_path, 
                                                               original_name)
                # Make and modify network
                network = self._generate_nice_CX_from_csv(result_csv_file_path, 
                                                          self._get_load_plan())
                self._add_network_attributes(network, original_name)
                self._add_network_style(network, self._get_template_network())
                cx_file_path = self._write_cx_to_file(network, original_name)
                
                # Upload network
                self._upload_cx(cx_file_path, original_name)

                #Clean up directory
                if not self._no_cleanup:
                    if file_is_xl:
                        os.remove(csv_file_path)
                    os.remove(result_csv_file_path)
                    os.remove(cx_file_path)
        return 0          

def main(args):
    #print('main')
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
