#! /usr/bin/env python

import argparse
from copy import deepcopy
from datetime import datetime
import json
import logging
from logging import config
import os
import re
import sys
import traceback

import bigjson
import csv
import mygene
import pandas as pd
import xlrd

import ndex2
from ndex2.client import Ndex2
import ndexutil.tsv.tsv2nicecx2 as t2n
from ndexutil.config import NDExUtilConfig
import ndexgenehancerloader

logger = logging.getLogger(__name__)
mg = mygene.MyGeneInfo()

LOG_FORMAT = "%(asctime)-15s %(levelname)s %(relativeCreated)dms " \
             "%(filename)s::%(funcName)s():%(lineno)d %(message)s"

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

NETWORK_ATTRIBUTES = 'networkattributes.json'
"""
Default network attributes file name
"""

PROFILE = 'ndexgenehancerloader'
"""
Default profile name
"""

UUID = 'uuid'
"""
Profile element for network UUIDs
"""

RESULT_PREFIX = '_result_'
INTERMEDIARY_PREFIX = '_intermediary_'
GENE_TYPES_PREFIX = '_genetypes_'
"""
Prefixes
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
    "EnhancerEnhancerType",
    "Gene",
    "GeneRep",
    "GeneEnhancerScore",
    "GeneType",
    "GeneGeneType"
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

ATTRIBUTE = 'attribute'
TYPE = 'type'
STRING = 'string'
"""
Network attribute type constants
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
    return _get_path(DATA_DIR)

def _get_default_load_plan_name():
    """
    Gets load plan stored with this package
    """
    return _get_path(os.path.join(get_package_dir(), LOAD_PLAN))

def _get_default_style_file_name():
    """
    Gets style network name
    """
    return _get_path(os.path.join(get_package_dir(), STYLE_FILE))

def _get_default_network_attributes_name():
    """
    Gets network attributes file name
    """
    return _get_path(os.path.join(get_package_dir(), NETWORK_ATTRIBUTES))

def _get_default_configuration_name():
    """
    Gets default configuration file
    """
    return _get_path(os.path.join('~/', NDExUtilConfig.CONFIG_FILE))

def _get_default_profile_name():
    return PROFILE

def _get_default_gene_types_name():
    return _get_path(os.path.join(get_package_dir(), GENE_TYPES))

def _get_path(file):
    return os.path.realpath(os.path.expanduser(file))

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
             '(default ' + DATA_DIR + ')'
    )
    parser.add_argument(
        '--updateuuid',
        '--update',
        default=None,
        help='The UUID of the network that is going to be updated. None of the '
             'network\'s properties or style will be affected unless the '
             '--version, --stylefile, or --styleprofile options are used.'
    )
    parser.add_argument(
        '--versionnumber',
        '--version',
        help='Version number of the new network'
    )
    parser.add_argument(
        '--loadplan', 
        default=_get_default_load_plan_name(),
        help='Load plan file that should be used (default ' + LOAD_PLAN + ')'
    )
    parser.add_argument(
        '--stylefile', 
        default=None,
        help='Name of template network file whose style should be used '
             '(default ' + STYLE_FILE + ')'
    )
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
             ' take precedence')
    parser.add_argument(
        '--genetypes',
        default=None,
        help='Json file that will be used to determine the types of genes.'
             '(default ' + GENE_TYPES + ')'
    )
    parser.add_argument(
        '--networkattributes',
        default=None,
        help='Json file containing the network\'s attributes. (default ' + 
             NETWORK_ATTRIBUTES + ')'
    )
    parser.add_argument(
        '--delimiter',
        default=None,
        help='Delimiter of the data file. (For tab enter the following: $\'\\t\')'
    )
    parser.add_argument(
        '--logconf', 
        default=None,
        help='Path to python logging configuration file in this format: '
             'https://docs.python.org/3/library/logging.config.html#logging-config-fileformat'
             '. Setting this overrides -v parameter which uses default logger. '
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
        help='If set, intermediary files generated in the data directory will '
             'not be removed')

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
        self._data_directory = _get_path(args.datadir)
        self._conf_file = args.conf
        self._load_plan_file = args.loadplan
        self._style_file = args.stylefile
        self._network_attributes_file = args.networkattributes
        self._no_header = args.noheader
        self._no_cleanup = args.nocleanup

        self._gene_types_file = args.genetypes
        self._update_gene_types = False
        if self._gene_types_file is None:
            self._update_gene_types = True
            self._gene_types_file = _get_default_gene_types_name()
        
        self._internal_gene_types = None

        self._delimiter = args.delimiter
        self._version = args.versionnumber
        
        self._style_network = None
        self._gene_types = None
        self._load_plan = None
        self._network_attributes = None

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

        self._update_uuid = args.updateuuid

    def _parse_config(self):
        """
        Parses config
        :return:
        """
        try:
            ncon = NDExUtilConfig(conf_file=self._conf_file)
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
            print("Error while parsing configuration file for style. "
                  "Default style template network (style.cx) will be used instead")
            return
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
    
    def _find_delimiter(self, file_name):
        if self._delimiter is None:
            if file_name.split('.')[-1] == 'tsv':
                self._delimiter = '\t'
            else:
                self._delimiter = ','

    def _get_file_path(self, file_name):
        return _get_path(os.path.join(self._data_directory, file_name))

    def _get_load_plan(self):
        try:
            with open(self._load_plan_file, 'r') as lp:
                self._load_plan = json.load(lp)
        except Exception as e:
            print(e)
            print("Error while loading load plan. "
                  "Default load plan will be used instead.")
            with open(_get_default_load_plan_name(), 'r') as lp:
                self._load_plan = json.load(lp)

    def _get_gene_types(self):
        try:
            with open(self._gene_types_file, 'rb') as gt:
                self._gene_types = json.load(gt)
        except Exception as e:
            print(e)
            print("Error while loading gene types. "
                  "Default gene types will be used instead.")
            self._gene_types_file = _get_default_gene_types_name()
            with open(self._gene_types_file, 'r') as gt:
                self._update_gene_types = True
                self._gene_types = json.load(gt)

    def _get_network_attributes(self):
        if self._network_attributes_file is not None:
            self._get_network_attributes_from_file()
        elif self._update_uuid is not None:
            self._get_network_attributes_from_uuid()
        else:
            self._network_attributes_file = _get_default_network_attributes_name()
            self._get_network_attributes_from_file()

        if self._version is not None:
            if 'version' in self._network_attributes:
                self._network_attributes['version']['attribute'] = self._version
            else:
                version = {
                    "attribute": self._version
                }
                self._network_attributes['version'] = version

    def _get_network_attributes_from_file(self):
        try:
            with open(self._network_attributes_file, 'r') as na:
                self._network_attributes = json.load(na)
        except Exception as e:
            print(e)
            print("Error while loading network attributes. "
                  "Default network attributes will be used instead.")
            with open(_get_default_network_attributes_name(), 'r') as na:
                self._network_attributes = json.load(na)

    def _get_network_attributes_from_uuid(self):
        response = self._ndex.get_network_as_cx_stream(self._update_uuid)
        network = ndex2.create_nice_cx_from_raw_cx(response.json())
        names = network.get_network_attribute_names()
        network_attributes = {}
        for name in names:
            attribute = network.get_network_attribute(name)
            network_attributes[name] = {
                "attribute": attribute['v'],
                "type": attribute['d'] if 'd' in attribute else STRING
            }
        self._network_attributes = network_attributes

    def _get_style_network(self):
        if self._style_file is not None:
            self._get_style_network_from_file()
        elif self._style_profile is not None:
            self._get_style_network_from_uuid()
        elif self._update_uuid is not None:
            self._style_server = self._server
            self._style_user = self._user
            self._style_pass = self._pass
            self._style_uuid = self._update_uuid
            self._get_style_network_from_uuid()
        else:
            self._style_file = _get_default_style_file_name()
            self._get_style_network_from_file()

    def _get_style_network_from_file(self):
        try:
            self._style_network = ndex2.create_nice_cx_from_file(self._style_file)
        except Exception as e:
            print(e)
            print("Error while loading style network from file. "
                  "Default style network will be used instead.")
            try:
                self._style_network = ndex2.create_nice_cx_from_file(
                    _get_default_style_file_name())
            except Exception as e:
                print(e)
                print("Error while loading default style network from file. "
                      "No style will be applied.")
        
    def _get_style_network_from_uuid(self):
        try:
            self._style_network = ndex2.create_nice_cx_from_server(
                self._style_server if self._style_server is not None else self._server,
                username = self._style_user if self._style_user is not None else self._user,
                password = self._style_pass if self._style_pass is not None else self._pass,
                uuid = self._style_uuid
            )
        except Exception as e:
            print(e)
            print("Error while loading style network from NDEx. "
                  "Default style will be used instead.")
            self._style_file = _get_default_style_file_name()
            self._get_style_network_from_file()


    def _get_original_name(self, file_name):
        reverse_string = file_name[::-1]
        try:
            new_string = reverse_string.split(".", 1)[1]
            return new_string[::-1]
        except IndexError:
            return file_name

    def _get_default_header(self): 
        return DEFAULT_HEADER

    def _get_output_header(self):
        return OUTPUT_HEADER

    def _data_directory_exists(self):
        return os.path.exists(self._data_directory)

    def _file_is_xl(self, file_name):
        extension = file_name.split(".")[-1]
        if extension[0:2] == 'xl':
            return True
        return False

    def _convert_from_xl_to_csv(self, file_path, original_name):
        workbook = xlrd.open_workbook(file_path)
        sheet = workbook.sheet_by_index(0)

        new_csv_file_path = self._get_file_path(INTERMEDIARY_PREFIX + original_name + ".csv")
        new_csv_file = open(new_csv_file_path, 'w')
        wr = csv.writer(new_csv_file, quoting=csv.QUOTE_ALL)

        for row_num in range(sheet.nrows):
            wr.writerow(sheet.row_values(row_num))

        new_csv_file.close()
        self._delimiter = ','
        return new_csv_file_path

    def _create_ndex_connection(self):
        """
        creates connection to ndex
        """
        if self._ndex is None:
            self._ndex = Ndex2(host=self._server, 
                               username=self._user, 
                               password=self._pass)
        return self._ndex

    def _reformat_csv_file(self, csv_file_path, original_name, file_name):
        if self._gene_types is None:
            self._get_gene_types()
        if not self._update_gene_types and self._internal_gene_types is None:
            self._internal_gene_types = {}
        try:
            result_csv_file_path = self._get_file_path(RESULT_PREFIX + original_name + ".csv")

            with open(csv_file_path, 'r', encoding='utf-8-sig') as read_file:
                reader = csv.reader(read_file, delimiter=self._delimiter)
                with open(result_csv_file_path, 'w') as write_file:
                    writer = csv.writer(write_file)
                    writer.writerow(self._get_output_header())

                    for i, line in enumerate(reader):
                        if i == 0:
                            if self._no_header:
                                header = self._get_default_header()
                            else:
                                header = line
                                continue
                        elif i % 100 == 0:
                            print('{} - processing row {} of {}'.format(
                                str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                str(i), 
                                file_name))
                            
                        attributes = line[header.index('attributes')].split(";")

                        #Find enhancer attributes
                        enhancer_id = attributes[0].split("=")[1]
                        enhancer_rep = self._get_rep(enhancer_id)
                        if 'chrom' in header:
                            enhancer_chrom = line[header.index('chrom')]
                        else:
                            enhancer_chrom = line[header.index('#chrom')]
                        enhancer_start = line[header.index('start')]
                        enhancer_end = line[header.index('end')]
                        enhancer_enhancer_type = line[header.index('feature name')]
                        enhancer_confidence_score = line[header.index('score')]

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
                            gene_gene_type = self._get_gene_type(gene_name)
                            writer.writerow([
                                enhancer_id,
                                enhancer_rep,
                                enhancer_chrom,
                                enhancer_start,
                                enhancer_end,
                                enhancer_confidence_score,
                                ENHANCER,
                                enhancer_enhancer_type,
                                gene_name,
                                gene_rep,
                                gene_enhancer_score,
                                GENE,
                                gene_gene_type
                            ])
            return result_csv_file_path
        except Exception as e:
            print(traceback.format_exc())
            print(e)

    def _get_gene_type(self, gene_name):
        # Match known genes
        if gene_name in self._gene_types:
            return self._gene_types[gene_name]
        if not self._update_gene_types and gene_name in self._internal_gene_types:
            return self._internal_gene_types[gene_name]    

        gene_type = None

        # Match known types
        if (re.match('^LINC[0-9-]+$', gene_name) or
            re.match('^LOC[0-9-]+$', gene_name) or
            re.match('^GC([0-9]+|MT)[A-Z]+[0-9]+', gene_name)):
            gene_type = "ncRNA gene"

        # Use mygene.info
        else:
            gene_type = self._get_gene_type_from_gene_info(gene_name)
            
            # Use known prefix
            if (gene_type is None and 
               (re.match('^RF[0-9]{5}', gene_name) or
                re.match('^HSALNG[0-9]+', gene_name) or
                re.match('^(M|m|P|p)(I|i)(R|r)', gene_name) or
                re.match('^(L|l)(N|n)(C|c)', gene_name) or
                re.match('^[A-Z]{2}[0-9-]+$', gene_name) or
                re.match('^5[A-Z0-9]{3}_', gene_name) or
                re.match('^hsa-miR-[0-9-]+', gene_name) or 
                re.match('^NONHSAG[0-9-.]+$', gene_name) or 
                re.match('^(L|Z)[0-9-]+', gene_name) or
                re.match('^SNOR[A-Z0-9-]+$', gene_name))): #Given exceptions in genetypes file
                gene_type = 'ncRNA gene'

        if gene_type is None:
            gene_type = 'Other gene'
        if self._update_gene_types:
            self._gene_types[gene_name] = gene_type
        else:
            self._internal_gene_types[gene_name] = gene_type
        return gene_type

    def _get_gene_type_from_gene_info(self, gene_name):
        gene_info = mg.query(gene_name, fields='type_of_gene,ensembl.type_of_gene')
        if gene_info is not None:
            for entry in gene_info['hits']:
                try:
                    gene_type = self._map_gene_type(entry['type_of_gene'])
                    if gene_type is not None:
                        return gene_type
                except KeyError:
                    pass
        
            for entry in gene_info['hits']:
                try:
                    ensembl_info = entry['ensembl']
                    gene_type = self._map_gene_type(ensembl_info['type_of_gene'])
                    if gene_type is not None:
                        return gene_type
                except KeyError:
                    pass
        return None

    def _map_gene_type(self, original_gene_type):
        for key in TYPE_OF_GENE_TO_GENE_TYPE_MAP:
            for regex in TYPE_OF_GENE_TO_GENE_TYPE_MAP[key]:
                if re.match(regex, original_gene_type):
                    return key

        return None

    def _get_rep(self, id):
        if re.match('^GH([0-9]{2}|MT|0X|0Y)[A-Z][0-9]+', id):
            return EN_GENECARDS + id
        else:
            return P_GENECARDS + id


    def _generate_nice_cx_from_csv(self, csv_file_path):
        if self._load_plan is None:
            self._get_load_plan()
        dataframe = pd.read_csv(csv_file_path,
                                dtype=str,
                                na_filter=False,
                                sep=",",
                                engine='python')
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(dataframe, self._load_plan)
        return network

    def _add_network_attributes(self, network, original_name):
        if self._network_attributes is None:
            self._get_network_attributes()
        
        has_name = False
        for attribute_name, attribute_object in self._network_attributes.items():
            if attribute_name == 'name':
                network.set_name(attribute_object[ATTRIBUTE])
                has_name = True
            elif attribute_name == 'prov:wasGeneratedBy':
                network.set_network_attribute(
                    attribute_name, 
                    attribute_object[ATTRIBUTE].format(version=ndexgenehancerloader.__version__),
                    type=STRING
                )
            else:
                network.set_network_attribute(
                    attribute_name, 
                    attribute_object[ATTRIBUTE], 
                    type=attribute_object[TYPE] if TYPE in attribute_object else STRING
                )
        
        if not has_name:
            network.set_name(original_name)
        
        return network.get_name()

    def _add_network_style(self, network):
        if self._style_network is None:
            self._get_style_network()
        network.apply_style_from_network(self._style_network)
        
    def _write_cx_to_file(self, network, original_name):
        cx_file_path = self._get_file_path(RESULT_PREFIX + original_name + ".cx")
        with open(cx_file_path, 'w') as f:
            json.dump(network.to_cx(), f, indent=4)
        return cx_file_path

    def _write_gene_type_to_file(self, original_name):
        if self._update_gene_types and self._gene_types is not None:
            with open(self._gene_types_file, 'w') as f:
                json.dump(self._gene_types, f, indent=4)
            return self._gene_types_file
        elif self._internal_gene_types is not None:
            gene_type_file_path = self._get_file_path(GENE_TYPES_PREFIX + original_name + ".json")
            with open(gene_type_file_path, 'w') as f:
                json.dump(self._internal_gene_types, f, indent=4)
            return gene_type_file_path

    def _upload_cx(self, cx_file_path, network_name):
        with open(cx_file_path, 'rb') as network_out:
            try:
                if self._update_uuid is None:
                    print('{} - started uploading "{}" on {} for user {}...'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                 network_name, 
                                 self._server, 
                                 self._user))
                    self._ndex.save_cx_stream_as_new_network(network_out)
                    print('{} - finished uploading "{}" on {} for user {}'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
                                 network_name, 
                                 self._server, 
                                 self._user))
                else:
                    print('{} - started updating "{}" on {} for user {}...'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                 network_name,
                                 self._server, 
                                 self._user))
                    self._ndex.update_cx_network(network_out, self._update_uuid)
                    print('{} - finished updating "{}" on {} for user {}'.
                          format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                                 network_name,
                                 self._server, 
                                 self._user))

            except Exception as e:
                print('{} - unable to update or upload "{}" on {} for user {}'.
                      format(str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                             network_name,
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
            if self._ndex is None:
                print("Error occured while connecting to ndex")
                return 2

            # Turn data into network
            if len(os.listdir(self._data_directory)) == 0:
                print("No files found in directory: {}".format(self._data_directory))
                return 2

            else:
                for file_name in os.listdir(self._data_directory):
                    try:
                        return_value = None

                        # Skip files that result from this process
                        if (file_name.startswith(RESULT_PREFIX) or 
                            file_name.startswith(INTERMEDIARY_PREFIX) or
                            file_name.startswith(GENE_TYPES_PREFIX) or
                            file_name.startswith('.')):
                            continue

                        print('\n{} - started processing "{}"...'.format(
                            str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")), 
                            file_name))
                        original_name = self._get_original_name(file_name)
                        
                        # Check for file type
                        file_is_xl = self._file_is_xl(file_name)
                        if file_is_xl:
                            xl_file_path = self._get_file_path(file_name)
                            csv_file_path = self._convert_from_xl_to_csv(xl_file_path, 
                                                                        original_name)
                        else:
                            self._find_delimiter(file_name)
                            csv_file_path = self._get_file_path(file_name)
                        
                        # Reformat csv into network
                        result_csv_file_path = self._reformat_csv_file(
                            csv_file_path, 
                            original_name,
                            file_name)
                        # Make and modify network
                        print('{} - generating network...'.format(
                            str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
                        network = self._generate_nice_cx_from_csv(result_csv_file_path)
                        network_name = self._add_network_attributes(network, original_name)
                        self._add_network_style(network)
                        cx_file_path = self._write_cx_to_file(network, original_name)
                        
                        # Upload network
                        return_value = self._upload_cx(cx_file_path, network_name)

                    except Exception as e:
                        print(e)
                        print(traceback.format_exc())
                        return 2
                    finally:
                        written = False
                        if return_value is not None:
                            if return_value == 0:
                                if self._no_cleanup:
                                    self._write_gene_type_to_file(original_name)
                                    written = True
                                else:
                                    if file_is_xl:
                                        os.remove(csv_file_path)
                                    os.remove(result_csv_file_path)
                                    os.remove(cx_file_path)
                            else:
                                self._write_gene_type_to_file('')
                                written = True
                            return return_value
                        if not written:
                            self._write_gene_type_to_file('')
        except Exception as e:
            print(e)
            print(traceback.format_exc())

def main(args):
    """
    Main entry point for program
    :param args:
    :return:
    """
    desc = """
    Version {version}

    Loads GeneHancer data into NDEx (http://ndexbio.org).
    
    To connect to NDEx server a configuration file must be passed
    into --conf parameter. If --conf is unset, then ~/{confname} 
    is examined. 
         
    The configuration file should be formatted as follows:
         
    [<value in --profile (default ndexgenehancerloader)>]
         
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
