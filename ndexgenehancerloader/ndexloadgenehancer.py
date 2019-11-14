#! /usr/bin/env python

import argparse
import csv
from datetime import datetime
import json
import logging
from logging import config
import mygene
import os
import pandas as pd
import re
import requests
import sys
import urllib
import xlrd
import traceback

import ndex2
from ndex2.client import Ndex2
import ndexutil.tsv.tsv2nicecx2 as t2n
import ndexgenehancerloader
from ndexutil.config import NDExUtilConfig

logger = logging.getLogger(__name__)
mg = mygene.MyGeneInfo()

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

STYLE_FILE = 'style.cx'
"""
Default name of style file
"""

GENE_TYPES = 'genetypes.json'
"""
Default name of gene type file
"""

PROFILE = 'ndexgenehancerloader'
"""
Default profile name
"""

UUID = 'uuid'
"""
Profile element for network UUIDs
"""

DEFAULT_HEADER = [
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

OUTPUT_HEADER = [
    "Enhancer",
    "EnhancerRep",
    "Chromosome",
    "StartLocation",
    "EndLocation",
    "EnhancerConfidenceScore",
    "EnhancerType",
    "EnhancerGeneType",
    "Gene",
    "GeneRep",
    "GeneEnhancerScore",
    "GeneType",
    "GeneGeneType"
]

GENEHANCER_URL = 'https://www.genecards.org/GeneHancer_version_4-4'
"""
Url that data is downloaded from
"""

GENEHANCER_IDS_THAT_DONT_EXIST = [
    'LOC105377711',
    'GH02F070017',
    'ENSG00000252213'
]

P_GENECARDS = 'p-genecards:'
EN_GENECARDS = 'en-genecards:'
"""
Namespace constants
"""

ENHANCER = 'enhancer'
GENE = 'gene'
"""
Node type constants
"""

NETWORK_DESCRIPTION_ATTRIBUTE = 'description'
NETWORK_REFERENCE_ATTRIBUTE = 'reference'
NETWORK_TYPE_ATTRIBUTE = 'networkType'
NETWORK_ICON_URL_ATTRIBUTE = '__iconurl'
NETWORK_GENERATED_BY_ATTRIBUTE = 'prov:wasGeneratedBy'
NETWORK_DERIVED_FROM_ATTRIBUTE = 'prov:wasDerivedFrom'
"""
Network attribute name constants
"""

LIST_OF_STRING = 'list_of_string'
"""
Network attribute type constants
"""

NETWORK_DESCRIPTION = """
    GeneHancer dataset {network_name} uploaded as a cytoscape network.
    """
NETWORK_REFERENCE = """
    Fishilevich S, Nudel R, Rappaport N, et al. GeneHancer: genome-wide 
    integration of enhancers and target genes in GeneCards. 
    <em>Database (Oxford).</em> 2017;2017:bax028. 
    <a href=http://doi.org/10.1093/database/bax028 
    target="_blank">doi:10.1093/database/bax028</a>
    """
NETWORK_TYPE = ["interactome", "geneassociation"]
NETWORK_ICON_URL = 'https://www.genecards.org/Images/Companions/Logo_GH.png'
NETWORK_GENERATED_BY = """
    <a href="https://github.com/ndexcontent/ndexgenehancerloader"
    target="_blank">ndexgenehancerloader {version} </a>
    """
NETWORK_DERIVED_FROM = ('<a href="' + 
                        GENEHANCER_URL + 
                        '" target="_blank">' + 
                        GENEHANCER_URL + 
                        '</a>') 
"""
Network attributes
"""

TYPE_OF_GENE_TO_GENE_TYPE_MAP = {
    'Protein coding gene': [
        'protein(_|-)coding',
        'IG_(C|D|J|LV|V)_gene'
    ],
    'ncRNA gene': [
        '.*RNA',
        'ribozyme'
    ],
    'Other gene': [
        '.*pseudo.*',
        'TEC',
        'other',
        'unknown'
    ]
}

def get_package_dir():
    """
    Gets directory where package is installed
    :return:
    """
    return os.path.dirname(ndexgenehancerloader.__file__)

def _get_default_data_dir_name():
    """
    Gets default data directory
    """
    return DATA_DIR

def _get_default_load_plan_name():
    """
    Gets load plan stored with this package
    """
    return os.path.join(get_package_dir(), LOAD_PLAN)

def _get_default_style_file_name():
    """
    Gets style network name
    """
    return os.path.join(get_package_dir(), STYLE_FILE)

def _get_default_configuration_name():
    """
    Gets default configuration file
    """
    return os.path.join('~/', NDExUtilConfig.CONFIG_FILE)

def _get_default_profile_name():
    return PROFILE

def _get_default_gene_types_name():
    return os.path.join(get_package_dir(), GENE_TYPES)

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
    parser.add_argument(
        '--datadir', 
        default=_get_default_data_dir_name(),
        help='Directory that GeneHancer data is found and processed in '
             '(default ' + DATA_DIR + ')')
    parser.add_argument(
        '--loadplan', 
        default=_get_default_load_plan_name(),
        help='Load plan file that should be used (default ' + LOAD_PLAN + ')')
    parser.add_argument(
        '--stylefile', 
        default=None,
        help='Name of template network file whose style should be used '
             '(default ' + STYLE_FILE + ')')
    parser.add_argument(
        '--conf', 
        default=_get_default_configuration_name(),
        help='Configuration file to load (default ~/' 
             + NDExUtilConfig.CONFIG_FILE + ')')
    parser.add_argument(
        '--profile', 
        default=_get_default_profile_name(),
        help='Profile in configuration file to use to load NDEx credentials ' 
             'which means configuration under [XXX] will be used '
             '(default ndexgenehancerloader)')
    parser.add_argument(
        '--styleprofile',
        default=None,
        help='Profile in configuration file to use to load template network for'
             'style. The following format should be used:'
             '[<value in --styleprofile>]'
             'user = <NDEx username>'
             'password = <NDEx password>'
             'server = <NDEx server>'
             'uuid = <UUID of template network>'
             ''
             'If --styleprofile and --stylefile are both used, --stylefile will'
             'take precedence')
    parser.add_argument(
        '--genetypes',
        default=_get_default_gene_types_name(),
        help='Json file that will be used to determine the types of genes.'
             '(default ' + GENE_TYPES + ')'
    )
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
    parser.add_argument(
        '--nogenetype',
        action='store_true',
        default=False,
        help='If set, gene types for each gene will not be fetched, and network'
             'processing will take several minutes instead of hours'
    )

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
        """
        :param args:
        """
        self._data_directory = os.path.abspath(args.datadir)
        self._conf_file = args.conf
        self._load_plan_file = args.loadplan
        self._style_file = args.stylefile
        self._gene_types_file = args.genetypes
        self._no_header = args.noheader
        self._no_cleanup = args.nocleanup
        self._no_gene_type = args.nogenetype

        self._style_network = None
        self._gene_types = None
        self._load_plan = None

        self._profile = args.profile
        self._user = None
        self._pass = None
        self._server = None

        self._style_profile = args.styleprofile
        self._style_user = None
        self._style_pass = None
        self._style_server = None
        self._style_uuid = None

        self._ndex = None
        self._network_summaries = None
        self._internal_gene_types = None

    def _get_path(self, file):
        return os.path.abspath(os.path.realpath(os.path.expanduser(file)))

    def _parse_config(self):
        """
        Parses config
        :return:
        """
        try:
            ncon = NDExUtilConfig(conf_file=os.path.expanduser(self._conf_file))
            con = ncon.get_config()
            self._user = con.get(self._profile, NDExUtilConfig.USER)
            self._pass = con.get(self._profile, NDExUtilConfig.PASSWORD)
            self._server = con.get(self._profile, NDExUtilConfig.SERVER)
        except Exception as e:
            print(e)
            raise
    
        if self._style_file is None and self._style_profile is not None:
            self._parse_style_config()

    def _parse_style_config(self):
        try:
            ncon = NDExUtilConfig(conf_file=os.path.expanduser(self._conf_file))
            con = ncon.get_config()
            self._style_uuid = con.get(self._style_profile, UUID)
        except Exception as e:
            self._style_profile = None
            print(e)
            print("Default style template network (style.cx) will be used instead")
        try:
            self._style_server = con.get(self._style_profile, NDExUtilConfig.SERVER)
        except Exception as e:
            print(e)
        try:
            self._style_user = con.get(self._style_profile, NDExUtilConfig.USER)
        except Exception as e:
            print(e)
        try:
            self._style_pass = con.get(self._style_profile, NDExUtilConfig.PASSWORD)
        except Exception as e:
            print(e)

    def _get_file_path(self, file_name):
        return self._data_directory + "/" + file_name

    def _get_load_plan(self):
        with open(self._load_plan_file, 'r') as lp:
            plan = json.load(lp)
        self._load_plan = plan

    def _get_gene_types(self):
        try:
            with open(self._gene_types_file, 'r') as lp:
                types = json.load(lp)
                self._gene_types = types
        except Exception as e:
            print(e)

    def _get_style_network(self):
        if self._style_file is None:
            if self._style_profile is not None:
                return self._get_style_network_from_uuid()
            else:
                self._style_file = _get_default_style_file_name()
        return self._get_style_network_from_file()

    def _get_style_network_from_file(self):
        if self._style_network is None:
            self._style_network = ndex2.create_nice_cx_from_file(self._style_file)
        return self._style_network

    def _get_style_network_from_uuid(self):
        if self._style_network is None:
            self._style_network = ndex2.create_nice_cx_from_server(
                self._style_server if self._style_server is not None else self._server,
                username = self._style_user if self._style_user is not None else self._user,
                password = self._style_pass if self._style_pass is not None else self._pass,
                uuid = self._style_uuid
            )
        return self._style_network

    def _get_server_and_uuid_from_ndex_url(self, url):
        splitUrl = url.split('#/network/')
        return splitUrl[0], splitUrl[1]

    def _get_original_name(self, file_name):
        reverse_string = file_name[::-1]
        new_string = reverse_string.split(".", 1)[1]
        return new_string[::-1]

    def _get_default_header(self): 
        return DEFAULT_HEADER

    def _get_output_header(self):
        return OUTPUT_HEADER

    def _data_directory_exists(self):
        return os.path.exists(self._data_directory)

    def _file_is_xl(self, file_name):
        reverse_string = file_name[::-1]
        index = reverse_string.find('.')
        if reverse_string[index-2 : index] == 'lx':
            return True
        return False

    def _convert_from_xl_to_csv(self, file_path, original_name):
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
        if self._gene_types is None:
            self._get_gene_types()
        if self._internal_gene_types is None:
            self._internal_gene_types = {}
        try:
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
                            if i % 100 == 0:
                                print(i)
                            attributes = line[header.index('attributes')].split(";")

                            #Find enhancer attributes
                            enhancer_id = attributes[0].split("=")[1]
                            enhancer_rep = self._get_rep(enhancer_id)
                            enhancer_chrom = line[header.index('chrom')]
                            enhancer_start = line[header.index('start')]
                            enhancer_end = line[header.index('end')]
                            enhancer_confidence_score = line[header.index('score')]
                            enhancer_gene_type = ''

                            #Take care of trailing semi-colons
                            if len(attributes) % 2 == 0:
                                iRange = len(attributes) - 1
                            else:
                                iRange = len(attributes)
                    
                            #Find genes
                            for i in range(1, iRange, 2):
                                gene_name = attributes[i].split("=")[1]
                                gene_rep = self._get_rep(gene_name)
                                gene_enhancer_score = attributes[i+1].split("=")[1]
                                gene_gene_type = ''
                                if not self._no_gene_type:
                                    gene_gene_type = self._get_gene_type(gene_name)
                                writer.writerow([
                                    enhancer_id,
                                    enhancer_rep,
                                    enhancer_chrom,
                                    enhancer_start,
                                    enhancer_end,
                                    enhancer_confidence_score,
                                    ENHANCER,
                                    enhancer_gene_type,
                                    gene_name,
                                    gene_rep,
                                    gene_enhancer_score,
                                    GENE,
                                    gene_gene_type
                                ])
            return result_csv_file_path
        except Exception as e:
            print(traceback.format_exc())

    def _get_gene_type(self, gene_name):
        # Match known genes
        if gene_name in self._gene_types:
            return self._gene_types[gene_name]
        if gene_name in self._internal_gene_types:
            return self._internal_gene_types[gene_name]    

        gene_type = None

        # Match known types
        if (re.match('^LINC[0-9]+$', gene_name) or
            re.match('^LOC[0-9]+$', gene_name) or
            re.match('^GC([0-9]+|MT)[A-Z]+[0-9]+', gene_name)):
            gene_type = "ncRNA gene"

        # Use mygene.info
        else:
            potential_gene_type = self._get_gene_type_from_gene_info(gene_name)
            if potential_gene_type is not None:
                gene_type = potential_gene_type    
            
            # Use known prefix
            elif gene_name[0:3] == 'PIR' or gene_name[0:3] == 'MIR':
                gene_type = 'ncRNA gene'

        if gene_type is None:
            self._internal_gene_types[gene_name] = 'Other gene'
            return 'Other gene'
        else:
            self._internal_gene_types[gene_name] = gene_type
            return gene_type

    def _get_gene_type_from_gene_info(self, gene_name):
        gene_info = mg.query(gene_name, fields='type_of_gene,ensembl.type_of_gene')
        if gene_info is not None:
            for entry in gene_info['hits']:
                try:
                    gene_type = self._map_gene_type(entry['type_of_gene'], gene_name)
                    if gene_type is not None:
                        return gene_type
                except KeyError:
                    pass
        
            for entry in gene_info['hits']:
                try:
                    ensembl_info = entry['ensembl']
                    gene_type = self._map_gene_type(ensembl_info['type_of_gene'], gene_name)
                    if gene_type is not None:
                        return gene_type
                except KeyError:
                    pass
        return None

    def _map_gene_type(self, original_gene_type, gene_name):
        try:
            for key in TYPE_OF_GENE_TO_GENE_TYPE_MAP:
                for regex in TYPE_OF_GENE_TO_GENE_TYPE_MAP[key]:
                    if re.match(regex, original_gene_type):
                        return key
        except KeyError:
            print('key error')

        return None

    def _get_rep(self, id):
        if id in GENEHANCER_IDS_THAT_DONT_EXIST:
            return ''
        if re.match('^GH([0-9]{2}|MT)[A-Z][0-9]+', id):
            return EN_GENECARDS + id
        else:
            return P_GENECARDS + id


    def _generate_nice_cx_from_csv(self, csv_file_path):
        if self._load_plan is None:
            self._get_load_plan()
        dataframe = pd.read_csv(csv_file_path,
                                dtype=str,
                                na_filter=False,
                                delimiter=',',
                                engine='python')
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, self._load_plan)
        return network

    def _add_network_attributes(self, network, original_name):
        network.set_name(original_name)
        network.set_network_attribute(
            NETWORK_DESCRIPTION_ATTRIBUTE, 
            NETWORK_DESCRIPTION.
            format(network_name=original_name)) 
        network.set_network_attribute(
            NETWORK_REFERENCE_ATTRIBUTE, 
            NETWORK_REFERENCE) 
        network.set_network_attribute(
            NETWORK_TYPE_ATTRIBUTE, 
            NETWORK_TYPE, 
            type=LIST_OF_STRING)
        network.set_network_attribute(
            NETWORK_ICON_URL_ATTRIBUTE,
            NETWORK_ICON_URL)
        network.set_network_attribute(
            NETWORK_GENERATED_BY_ATTRIBUTE,
            NETWORK_GENERATED_BY.
            format(version=ndexgenehancerloader.__version__))
        network.set_network_attribute(
            NETWORK_DERIVED_FROM_ATTRIBUTE,
            NETWORK_DERIVED_FROM
        )

    def _add_network_style(self, network):
        try:
            network.apply_style_from_network(self._get_style_network())
        except Exception as e:
            print(e)
        
    def _write_cx_to_file(self, network, original_name):
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
                return 2
        return 0 

    def run(self):
        try:
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
                    network = self._generate_nice_cx_from_csv(result_csv_file_path)
                    self._add_network_attributes(network, original_name)
                    self._add_network_style(network)
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
        except Exception as e:
            print(traceback.format_exc())

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
