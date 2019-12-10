#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `ndexgenehancerloader` package."""

import os
import tempfile
import shutil
import unittest
import csv
import json
import sys
from contextlib import contextmanager
from io import StringIO
import traceback
import pandas as pd
import xlwt
from xlwt import Workbook

from ndexutil.config import NDExUtilConfig
import ndexgenehancerloader
from ndexgenehancerloader import ndexloadgenehancer
from ndexgenehancerloader.ndexloadgenehancer import NDExGeneHancerLoader
import ndexutil.tsv.tsv2nicecx2 as t2n
import ndex2
from ndex2.client import Ndex2

@contextmanager
def captured_output():
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err

class Param(object):
    """
    Dummy object
    """
    pass

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

class TestNdexgenehancerloader(unittest.TestCase):
    """Tests for 'ndexgenehancerloader' package"""

    def setUp(self):
        """Set up test fixtures, if any"""
        self._args = {
            'datadir': tempfile.mkdtemp(),
            'genetypes': ndexloadgenehancer._get_default_gene_types_name(),
            'conf': None,
            'loadplan': None,
            'style': None,
            'styleprofile': None,
            'profile': None,
            'logconf': None,
            'verbose': 2,
            'noheader': None,
            'nocleanup': None
        }
        self._args = dotdict(self._args)
        self._user = 'sophieTest'
        self._password = 'test12345'
        self._server = 'dev.ndexbio.org'
        self._test_network_uuid = '2ee6d4f9-0afb-11ea-8612-525400c25d22'
        self._test_style_network_uuid = '243fca04-17ae-11ea-a0f6-525400c25d22'

        self._ndex_client = Ndex2(host=self._server, 
                                  username=self._user,
                                  password=self._password)
        
        self._network_data = [['source1', 'target1'], ['source2', 'target2']]
        self._network_data_header = ['source', 'target']
        self._load_plan = {
            "source_plan": {
                "node_name_column": "source"
            },
            "target_plan": {
                "node_name_column": "target"
            },
            "edge_plan": {
                "default_predicate": "affects"
            }
        }

    def tearDown(self):
        """Tear down test fixtures, if any"""
        if os.path.exists(self._args['datadir']):
            shutil.rmtree(self._args['datadir'])

    def testget_package_dir(self):
        actual_package_dir = ndexloadgenehancer.get_package_dir()
        expected_package_dir = os.path.dirname(ndexgenehancerloader.__file__)
        self.assertEqual(actual_package_dir, expected_package_dir)

    def test_get_default_data_dir_name(self):
        actual_datadir = ndexloadgenehancer._get_default_data_dir_name()
        expected_datadir = os.path.realpath(
            os.path.expanduser(ndexloadgenehancer.DATA_DIR))
        self.assertEqual(actual_datadir, expected_datadir)

    def test_get_default_load_plan_name(self):
        actual_load_plan = ndexloadgenehancer._get_default_load_plan_name()
        expected_load_plan = os.path.join(ndexloadgenehancer.get_package_dir(), ndexloadgenehancer.LOAD_PLAN)
        self.assertEqual(actual_load_plan, expected_load_plan)

    def test_get_default_style_file_name(self):
        actual_style = ndexloadgenehancer._get_default_style_file_name()
        expected_style = os.path.join(ndexloadgenehancer.get_package_dir(), ndexloadgenehancer.STYLE_FILE)
        self.assertEqual(actual_style, expected_style)

    def test_get_default_configuration_name(self):
        actual_config = ndexloadgenehancer._get_default_configuration_name()
        expected_config = os.path.realpath(
            os.path.expanduser(
                os.path.join('~/', NDExUtilConfig.CONFIG_FILE)))
        self.assertEqual(actual_config, expected_config)

    def test_get_default_profile_name(self):
        actual_profile = ndexloadgenehancer._get_default_profile_name()
        expected_profile = ndexloadgenehancer.PROFILE
        self.assertEqual(actual_profile, expected_profile)

    def test_get_default_gene_types_name(self):
        actual_gene = ndexloadgenehancer._get_default_gene_types_name()
        expected_gene = os.path.join(ndexloadgenehancer.get_package_dir(), ndexloadgenehancer.GENE_TYPES)
        self.assertEqual(actual_gene, expected_gene)

    def test_get_path(self):
        expected_path = os.path.realpath(os.path.expanduser('file'))
        actual_path = ndexloadgenehancer._get_path('file')
        self.assertEqual(actual_path, expected_path)

    def test_parse_arguments(self):
        self.maxDiff = None
        desc = """
        Version {version}
        Loads NDEx GeneHancer Content Loader data into NDEx (http://ndexbio.org).
        To connect to NDEx server a configuration file must be passed
        into --conf parameter. If --conf is unset, the configuration
        ~/{confname} is examined.
        The configuration file should be formatted as follows:
        [<value in --profile (default dev)>]
        {user} = <NDEx username>
        {password} = <NDEx password>
        {server} = <NDEx server(omit http) ie public.ndexbio.org>
        """.format(confname=NDExUtilConfig.CONFIG_FILE,
                   user=NDExUtilConfig.USER,
                   password=NDExUtilConfig.PASSWORD,
                   server=NDExUtilConfig.SERVER,
                   version=ndexgenehancerloader.__version__)
        
        temp_dir = self._args['datadir']

        #Test default args
        args = []
        expected_default_args = {}
        expected_default_args['datadir'] = ndexloadgenehancer._get_default_data_dir_name()
        expected_default_args['updateuuid'] = None
        expected_default_args['versionnumber'] = None
        expected_default_args['loadplan'] = ndexloadgenehancer._get_default_load_plan_name()
        expected_default_args['stylefile'] = None
        expected_default_args['conf'] = ndexloadgenehancer._get_default_configuration_name()
        expected_default_args['profile'] = 'ndexgenehancerloader'
        expected_default_args['styleprofile'] = None
        expected_default_args['genetypes'] = None
        expected_default_args['networkattributes'] = None
        expected_default_args['delimiter'] = None
        expected_default_args['logconf'] = None
        expected_default_args['verbose'] = 0
        expected_default_args['noheader'] = False
        expected_default_args['nocleanup'] = False

        default_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(default_args.__dict__, expected_default_args)

        #Test new args
        args.append('--datadir')
        args.append('new_dir')
        args.append('--updateuuid')
        args.append('new_uuid')
        args.append('--versionnumber')
        args.append('new_version')
        args.append('--loadplan')
        args.append('new_load_plan')
        args.append('--stylefile')
        args.append('new_style_file')
        args.append('--conf')
        args.append('new_conf')
        args.append('--profile')
        args.append('new_profile')
        args.append('--styleprofile')
        args.append('new_style_profile')
        args.append('--genetypes')
        args.append('new_gene_types')
        args.append('--networkattributes')
        args.append('new_network_attributes')
        args.append('--delimiter')
        args.append('new_delimiter')
        args.append('--logconf')
        args.append('new_log_conf')
        args.append('--verbose')
        args.append('--noheader')
        args.append('--nocleanup')

        expected_args = {}
        expected_args['datadir'] = 'new_dir'
        expected_args['updateuuid'] = 'new_uuid'
        expected_args['versionnumber'] = 'new_version'
        expected_args['loadplan'] = 'new_load_plan'
        expected_args['stylefile'] = 'new_style_file'
        expected_args['conf'] = 'new_conf'
        expected_args['profile'] = 'new_profile'
        expected_args['styleprofile'] = 'new_style_profile'
        expected_args['genetypes'] = 'new_gene_types'
        expected_args['networkattributes'] = 'new_network_attributes'
        expected_args['delimiter'] = 'new_delimiter'
        expected_args['logconf'] = 'new_log_conf'
        expected_args['verbose'] = 1
        expected_args['noheader'] = True
        expected_args['nocleanup'] = True

        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_args)

        #Test verbose
        args = []
        args.append('-v')
        expected_default_args['verbose'] = 1
        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_default_args)

        args = []
        args.append('-vv')
        expected_default_args['verbose'] = 2
        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_default_args)

        args = []
        args.append('-vvv')
        expected_default_args['verbose'] = 3
        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_default_args)

        args = []
        args.append('-vvvv')
        expected_default_args['verbose'] = 4
        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_default_args)

        args = []
        args.append('-vvvvv')
        expected_default_args['verbose'] = 5
        the_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(the_args.__dict__, expected_default_args)

    def test_setup_logging(self):
        for verbose_level in range(1, 5):
            args = {
                'logconf': None,
                'verbose': verbose_level
            }
            args = dotdict(args)
            ndexloadgenehancer._setup_logging(args)
            logger_level_set = ndexloadgenehancer.logger.getEffectiveLevel()
            self.assertEqual((50 - (10 * verbose_level)), logger_level_set)

    def test__init__(self):
        args = {}
        args['datadir'] = 'my_data_dir'
        args['conf'] = 'my_config'
        args['loadplan'] = 'my_load_plan'
        args['stylefile'] = 'my_style_file'
        args['genetypes'] = 'my_gene_types'
        args['noheader'] = 'my_no_header'
        args['nocleanup'] = 'my_no_cleanup'
        args['profile'] = 'my_profile'
        args['styleprofile'] = 'my_style_profile'
        args = dotdict(args)
        loader = NDExGeneHancerLoader(args)

        self.assertEqual(loader._data_directory, os.path.realpath('my_data_dir'))
        self.assertEqual(loader._conf_file, 'my_config')
        self.assertEqual(loader._load_plan_file, 'my_load_plan')
        self.assertEqual(loader._style_file, 'my_style_file')
        self.assertEqual(loader._gene_types_file, 'my_gene_types')
        self.assertEqual(loader._no_header, 'my_no_header')
        self.assertEqual(loader._no_cleanup, 'my_no_cleanup')
        self.assertEqual(loader._profile, 'my_profile')
        self.assertEqual(loader._style_profile, 'my_style_profile')
        self.assertIsNone(loader._style_network)
        self.assertIsNone(loader._gene_types)
        self.assertIsNone(loader._load_plan)
        self.assertIsNone(loader._user)
        self.assertIsNone(loader._pass)
        self.assertIsNone(loader._server)
        self.assertIsNone(loader._style_user)
        self.assertIsNone(loader._style_pass)
        self.assertIsNone(loader._style_server)
        self.assertIsNone(loader._style_uuid)
        self.assertIsNone(loader._ndex)
        self.assertIsNone(loader._internal_gene_types) 

    def test_parse_config(self):
        # Set up variables
        self._args['conf'] = os.path.join(self._args['datadir'], 'test_conf')
        self._args['profile'] = 'test_profile'
        loader = NDExGeneHancerLoader(self._args)

        # Test working config
        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['profile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.flush()
        loader._parse_config()
        self.assertEqual('test_user', loader._user)
        self.assertEqual('test_password', loader._pass)
        self.assertEqual('test_server', loader._server)

        # Test configs that throw exceptions
        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['profile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader._parse_config()
            self.fail("Failed to throw exception when server was not in config")
        except:
            self.assertEqual(out.getvalue().strip(), "No option 'server' in section: '" + self._args['profile'] + "'")
            pass

        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['profile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader._parse_config()
            self.fail("Failed to throw exception when password was not in config")
        except:
            self.assertEqual(out.getvalue().strip(), "No option 'password' in section: '" + self._args['profile'] + "'")
            pass

        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['profile'] + ']\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader._parse_config()
            self.fail("Failed to throw exception when user was not in config")
        except:
            self.assertEqual(out.getvalue().strip(), "No option 'user' in section: '" + self._args['profile'] + "'")
            pass

        with open(self._args['conf'], 'w') as config:
            config.write('[wrong_profile]\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader._parse_config()
            self.fail("Failed to throw exception when profile was not in config")
        except:
            self.assertEqual(out.getvalue().strip(), "No section: '" + self._args['profile'] + "'")
            pass

        # Check if _parse_style_config is being called
        loader._style_profile = 'style'
        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['profile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write('[' + loader._style_profile + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(ndexloadgenehancer.UUID + ' = test_uuid')
            config.flush()
        loader._parse_config()
        self.assertIsNotNone(loader._style_profile)
        self.assertIsNotNone(loader._style_server)
        self.assertIsNotNone(loader._style_user)
        self.assertIsNotNone(loader._style_pass)
        self.assertIsNotNone(loader._style_uuid)
    
    def test_parse_style_config(self):
        # Set up variables
        self._args['conf'] = 'test_conf'#os.path.join(self._args['datadir'], 'test_conf')
        self._args['styleprofile'] = 'style'

        # Test working config
        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['styleprofile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(ndexloadgenehancer.UUID + ' = test_uuid')
            config.flush()
        loader = NDExGeneHancerLoader(self._args)
        loader._parse_style_config()
        self.assertEqual('test_user', loader._style_user)
        self.assertEqual('test_password', loader._style_pass)
        self.assertEqual('test_server', loader._style_server)
        self.assertEqual('test_uuid', loader._style_uuid)

        # Test configs that throw and catch errors
        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['styleprofile'] + ']\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(ndexloadgenehancer.UUID + ' = test_uuid')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader = NDExGeneHancerLoader(self._args)
                loader._parse_style_config()
                self.assertEqual(
                    out.getvalue().strip(), 
                    "No option 'user' in section: '" + 
                    self._args['styleprofile'] + 
                    "'")
            self.assertEqual('test_password', loader._style_pass)
            self.assertEqual('test_server', loader._style_server)
            self.assertEqual('test_uuid', loader._style_uuid)
            self.assertIsNone(loader._style_user)
        except:
            self.fail()

        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['styleprofile'] + ']\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(ndexloadgenehancer.UUID + ' = test_uuid')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader = NDExGeneHancerLoader(self._args)
                loader._parse_style_config()
                self.assertEqual(
                    out.getvalue().strip(), 
                    "No option 'password' in section: '" + 
                    self._args['styleprofile'] + 
                    "'")
            self.assertEqual('test_user', loader._style_user)
            self.assertEqual('test_server', loader._style_server)
            self.assertEqual('test_uuid', loader._style_uuid)
            self.assertIsNone(loader._style_pass)
        except:
            self.fail()

        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['styleprofile'] + ']\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.write(ndexloadgenehancer.UUID + ' = test_uuid')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader = NDExGeneHancerLoader(self._args)
                loader._parse_style_config()
                self.assertEqual(
                    out.getvalue().strip(), 
                    "No option 'server' in section: '" + 
                    self._args['styleprofile'] + 
                    "'")
            self.assertEqual('test_user', loader._style_user)
            self.assertEqual('test_password', loader._style_pass)
            self.assertEqual('test_uuid', loader._style_uuid)
            self.assertIsNone(loader._style_server)
        except:
            self.fail()

        with open(self._args['conf'], 'w') as config:
            config.write('[' + self._args['styleprofile'] + ']\n')
            config.write(NDExUtilConfig.PASSWORD + ' = test_password\n')
            config.write(NDExUtilConfig.SERVER + ' = test_server\n')
            config.write(NDExUtilConfig.USER + ' = test_user\n')
            config.flush()
        try:
            with captured_output() as (out, err):
                loader = NDExGeneHancerLoader(self._args)
                loader._parse_style_config()
                self.assertEqual(
                    out.getvalue().strip(), 
                    "No option 'uuid' in section: '" + 
                    self._args['styleprofile'] + 
                    "'\nError while parsing configuration file for style. Default style template network (style.cx) will be used instead")
                self.assertIsNone(loader._style_uuid)
                self.assertIsNone(loader._style_user)
                self.assertIsNone(loader._style_pass)
                self.assertIsNone(loader._style_server)
        except:
            self.fail()

    def test_find_delimiter(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._find_delimiter('file.tsv')
        self.assertEqual(loader.__getattribute__('_delimiter'), '\t')
        loader._find_delimiter('file.csv')
        self.assertEqual(loader.__getattribute__('_delimiter'), '\t')

        loader.__setattr__('_delimiter', None)
        loader._find_delimiter('file.csv')
        self.assertEqual(loader.__getattribute__('_delimiter'), ',')

    def test_get_file_path(self):
        loader = NDExGeneHancerLoader(self._args)
        expected_path = os.path.realpath(os.path.join(self._args['datadir'], 'file'))
        actual_path = loader._get_file_path('file')
        self.assertEqual(expected_path, actual_path)

    def test_get_load_plan(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._load_plan_file = ndexloadgenehancer._get_default_load_plan_name()
        
        loader._get_load_plan()
        self.assertIsNotNone(loader._load_plan)

    def test_get_load_plan_error(self):
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_load_plan_file', 'file')
        with captured_output() as (out, err):
            loader._get_load_plan()
            self.assertEqual(
                out.getvalue().strip(), 
                "[Errno 2] No such file or directory: 'file'"
                "\nError while loading load plan. "
                "Default load plan will be used instead.")
            self.assertIsNotNone(loader._load_plan)

    def test_get_gene_types(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._gene_types_file = ndexloadgenehancer._get_default_gene_types_name()

        loader._get_gene_types()
        self.assertIsNotNone(loader._gene_types)

    def test_get_gene_types_error(self):
        ndexloadgenehancer._setup_logging(self._args)
        loader = NDExGeneHancerLoader(self._args)

        loader.__setattr__('_gene_types_file', 'file')
        with captured_output() as (out, err):
            loader._get_gene_types()
            self.assertEqual(
                out.getvalue().strip(), 
                "[Errno 2] No such file or directory: 'file'"
                "\nError while loading gene types. "
                "Default gene types will be used instead.")
            self.assertIsNotNone(loader._gene_types)

    def test_get_network_attributes(self):
        # Setup
        attributes = {
            "name": "attribute"
        }
        attributes_file = os.path.join(self._args['datadir'], 'attributes_file')
        with open(attributes_file, 'w') as af:
            json.dump(attributes, af, indent=4)

        # Test default
        loader = NDExGeneHancerLoader(self._args)
        loader._get_network_attributes()
        self.assertEqual(
            loader._network_attributes_file, 
            ndexloadgenehancer._get_default_network_attributes_name())
        self.assertIsNotNone(loader._network_attributes)

        # Test with file
        args = {
            'datadir': 'dir',
            'networkattributes': attributes_file
        }
        args = dotdict(args)
        loader = NDExGeneHancerLoader(args)
        loader._get_network_attributes()
        self.assertEqual(loader._network_attributes['name'], 'attribute')

    def test_get_network_attributes_version(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._network_attributes_file = ndexloadgenehancer._get_default_network_attributes_name()
        loader._version = 'version'

        loader._get_network_attributes()
        version = {
            "attribute": 'version'
        }
        self.assertEqual(loader._network_attributes['version'], version)

    def test_get_network_attributes_from_uuid(self):
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_update_uuid', self._test_network_uuid)
        loader.__setattr__('_ndex', self._ndex_client)
        loader._get_network_attributes()
        self.assertIsNotNone(loader._network_attributes)       

    def test_get_network_attributes_from_file_error(self):
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_network_attributes_file', 'file')
        with captured_output() as (out, err):
            loader._get_network_attributes()
            self.assertEqual(
                out.getvalue().strip(), 
                "[Errno 2] No such file or directory: 'file'"
                "\nError while loading network attributes. "
                "Default network attributes will be used instead.")
            self.assertIsNotNone(loader._network_attributes)

    def test_get_style_network(self):
        # Setup
        loader = NDExGeneHancerLoader(self._args)

        # Test nothing is defined (use file)
        loader._get_style_network()
        self.assertEqual(len(loader._style_network.get_nodes()), 13)

        # Test just uuid is defined (use uuid)
        loader.__setattr__('_style_file', None)
        loader.__setattr__('_server', self._server)
        loader.__setattr__('_user', self._user)
        loader.__setattr__('_pass', self._password)
        loader.__setattr__('_update_uuid', self._test_network_uuid)
        loader._get_style_network()
        self.assertEqual(len(loader._style_network.get_nodes()), 4)

        # Test uuid and profile are defined (use profile)
        loader.__setattr__('_style_profile', True)
        loader.__setattr__('_style_server', self._server)
        loader.__setattr__('_style_user', self._user)
        loader.__setattr__('_style_pass', self._password)
        loader.__setattr__('_style_uuid', self._test_style_network_uuid)
        loader._get_style_network()
        self.assertEqual(len(loader._style_network.get_nodes()), 1)

        # Test uuid, profile, and file are all defined (use file)
        loader.__setattr__('_style_file', ndexloadgenehancer._get_default_style_file_name())
        loader._get_style_network()
        self.assertEqual(len(loader._style_network.get_nodes()), 13)

    def test_get_style_network_from_file(self):
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_style_file', ndexloadgenehancer._get_default_style_file_name())
        loader._get_style_network_from_file()
        
        expected_network = ndex2.create_nice_cx_from_file(ndexloadgenehancer._get_default_style_file_name())
        self.assertEqual(
            len(expected_network.get_nodes()), 
            len(loader._style_network.get_nodes()))

    def test_get_style_network_from_file_error(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._style_file = 'file'
        with captured_output() as (out, err):
            loader._get_style_network_from_file()
            self.assertEqual(
                out.getvalue().strip(),
                "The file file  does not exist."
                "\nError while loading style network from file. "
                "Default style network will be used instead."
            )
            self.assertIsNotNone(loader._style_network)

    
    def test_get_style_network_from_uuid(self):
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_server', self._server)
        loader.__setattr__('_user', self._user)
        loader.__setattr__('_pass', self._password)
        loader.__setattr__('_style_uuid', self._test_network_uuid)
        
        loader._get_style_network_from_uuid()
        self.assertEqual(len(loader._style_network.get_nodes()), 4)

        loader.__setattr__('_style_network', None)
        loader.__setattr__('_server', 'wrong_server')
        loader.__setattr__('_user', 'wrong_user')
        loader.__setattr__('_pass', 'wrong_password')
        loader.__setattr__('_style_server', self._server)
        loader.__setattr__('_style_user', self._user)
        loader.__setattr__('_style_pass', self._password)
        
        loader._get_style_network_from_uuid()
        self.assertEqual(len(loader._style_network.get_nodes()), 4)

    def test_get_style_network_from_uuid_error(self):
        loader = NDExGeneHancerLoader(self._args)
        with captured_output() as (out, err):
            loader._get_style_network_from_uuid()
            self.assertEqual(
                out.getvalue().strip(),
                "Server and uuid not specified"
                "\nError while loading style network from NDEx. "
                "Default style will be used instead."
            )
            self.assertIsNotNone(loader._style_network)

    def test_get_original_name(self):
        loader = NDExGeneHancerLoader(self._args)

        actual_name = loader._get_original_name('file.extension')
        self.assertEqual('file', actual_name)

        actual_name = loader._get_original_name('file.file.file.extension')
        self.assertEqual('file.file.file', actual_name)
    
    def test_get_default_header(self):
        loader = NDExGeneHancerLoader(self._args)
        actual_header = loader._get_default_header()
        expected_header = [
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
        self.assertEqual(actual_header, expected_header)

    def test_get_output_header(self):
        loader = NDExGeneHancerLoader(self._args)
        actual_header = loader._get_output_header()
        expected_header = [
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
        self.assertEqual(actual_header, expected_header)

    def test_data_directory_exists(self):
        loader = NDExGeneHancerLoader(self._args)
        self.assertTrue(loader._data_directory_exists())    

        loader.__setattr__('_data_directory', 'fakeDir')
        self.assertFalse(loader._data_directory_exists())

    def test_file_is_xl(self):
        xl_files = [
            'file.xls',
            'file.xlsx',
            'file.xlsm',
            'file.xlt',
            'file.xltx',
            'file.xltm',
            'file.xla',
            'file.xlam'
        ]
        non_xl_files = [
            'file.csv',
            'file.tsv',
            'file.cx',
            'file.png',
            'file.jpg',
            'file.xl.notxl'
        ]
        loader = NDExGeneHancerLoader(self._args)
        for file in xl_files:
            self.assertTrue(loader._file_is_xl(file))
        for file in non_xl_files:
            self.assertFalse(loader._file_is_xl(file))

    def test_convert_from_xl_to_csv(self):
        # Setup
        wb_file = os.path.join(self._args['datadir'], 'wb.xls') 
        wb = Workbook()
        sheet1 = wb.add_sheet('Sheet 1')
        alphabet = 'ABCDEFGHIJ'
        for i in range(10):
            for j in range(10):
                sheet1.write(i, j, alphabet[i] + alphabet[j])
        wb.save(wb_file)

        # Convert
        loader = NDExGeneHancerLoader(self._args)
        csv_file = loader._convert_from_xl_to_csv(wb_file, 'file_name')

        # Test
        self.assertEqual(csv_file,
            os.path.realpath(os.path.join(
                self._args['datadir'], 
                ndexloadgenehancer.INTERMEDIARY_PREFIX + 'file_name.csv')))
        
        with open(csv_file, 'r') as cf:
            reader = csv.reader(cf, delimiter=',')
            for i, line in enumerate(reader):
                for j in range(len(line)):
                    self.assertEqual(line[j], alphabet[i] + alphabet[j])

    def test_create_ndex_connection(self):
        loader = NDExGeneHancerLoader(self._args)

        loader.__setattr__('_server', self._server)
        loader.__setattr__('_user', self._user)
        loader.__setattr__('_pass', self._password)

        ndex_connection = loader._create_ndex_connection()
        self.assertIsNotNone(ndex_connection)

        user_obj = ndex_connection.get_user_by_username(self._user)
        self.assertTrue(len(user_obj) == 13)
        
        try:    
            ndex_connection.get_network_summaries_for_user(self._user)
        except Exception as e:
            self.fail("Exception while getting network summaries " + e)

    """
    def test_load_network_summaries_for_user(self):
        # Clean up in case delete "delete_me" network failed
        # in test_upload_cx
        network_summaries = self._ndex_client.get_network_summaries_for_user(self._user)
        uuid = None
        for summary in network_summaries:
            if summary.get('name') == 'delete_me':
                uuid = summary.get('externalId')
                returnString = self._ndex_client.delete_network(uuid, retry=10)

        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_user', self._user)
        loader.__setattr__('_ndex', self._ndex_client)

        self.assertEqual(loader._load_network_summaries_for_user(), 0)
        self.maxDiff = None
        expected_summaries = {
            "BIOGRID: PROTEIN-CHEMICAL INTERACTIONS (H. SAPIENS)" : 
                "c7cfc125-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (A. THALIANA)" :
                "c47d61d2-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (C. ELEGANS)" :
                "ad0562ef-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (D. RERIO)" :
                "a2836a1b-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (D. MELANOGASTER)" :
                "a1e68dd9-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (H. SAPIENS)" :
                "815526d6-fcf1-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (HIV-1)" :
                "b68b16d1-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (HIV-2)" :
                "b5c9747f-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (HPV)" :
                "b5baa76d-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (M. MUSCULUS)" :
                "b567574b-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (R. NORVEGICUS)" :
                "9e779b37-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (S. CEREVISIAE)" :
                "975ff685-fcf0-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (X. LAEVIS)" :
                "c59dcd2d-fcee-11e9-93e0-525400c25d22",
            "BIOGRID: PROTEIN-PROTEIN INTERACTIONS (Z. MAYS)" :
                "c4eb1efb-fcee-11e9-93e0-525400c25d22",
            "TEST" : self._test_network_uuid
        }

        actual_summaries = loader.__getattribute__('_network_summaries')
        self.assertEqual(actual_summaries, expected_summaries)
    
    def test_load_network_summaries_for_user_error(self):
        loader = NDExGeneHancerLoader(self._args)
        with captured_output() as (out, err):
            status = loader._load_network_summaries_for_user()
            self.assertEqual(status, 2)
            self.assertEqual(
                out.getvalue().strip(),
                "'NoneType' object has no attribute 'get_network_summaries_for_user'"
            )
    """
    def test_reformat_csv_file_no_header(self):
        try:
            # Make test csv file
            test_csv_file_path = os.path.join(self._args['datadir'], 'test.csv')
            with open(test_csv_file_path, 'w') as test_csv:
                writer = csv.writer(test_csv)
                alphabet = 'ABCDEFGHI'
                for i in range(10):
                    attributes_string = 'genehancer_id=GH' + str(i)
                    for j in range(i):
                        attributes_string += ';connected_gene='
                        attributes_string += 'fakegene:' + alphabet[i-1] + '-' + alphabet[j] + ';'
                        attributes_string += 'score='
                        attributes_string += str(i) + '.' + str(j)
                    if i % 2 == 0:
                        attributes_string += ';'
                    writer.writerow([
                        'chr' + str(i),
                        'GeneHancer',
                        'Enhancer' + str(i),
                        str(i),
                        str(i) + '000',
                        '0.' + str(i),
                        '.',
                        '.',
                        attributes_string
                    ])
            
            # Execute function that is being tested
            loader = NDExGeneHancerLoader(self._args)
            loader.__setattr__('_delimiter', ',')
            loader.__setattr__('_no_header', True)
            result_csv_file_path = loader._reformat_csv_file(test_csv_file_path, 
                                                             'test_csv_file',
                                                             'test_csv_file_name')

            # Check for correctness
            with open(result_csv_file_path, 'r') as result_csv:
                reader = csv.reader(result_csv, delimiter=',')
                i = 1
                j = 0
                for k, line in enumerate(reader):
                    if (k == 0):
                        expected_header = [
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
                        self.assertEqual(line, expected_header)
                    else:
                        expected_row = [
                            'GH' + str(i),
                            'p-genecards:GH' + str(i), 
                            'chr' + str(i),
                            str(i),
                            str(i) + '000',
                            '0.' + str(i),
                            'enhancer',
                            'Enhancer' + str(i),
                            'fakegene:' + alphabet[i-1] + '-' + alphabet[j],
                            'p-genecards:fakegene:' + alphabet[i-1] + '-' + alphabet[j],
                            str(i) + '.' + str(j),
                            'gene',
                            'Other gene'
                        ]
                        j += 1
                        if (j == i):
                            i += 1
                            j = 0
                        self.assertEqual(line, expected_row)
        except Exception as e:
            self.fail('Exception during test_reformat_csv_file ' + str(e))
    
    def test_reformat_csv_file_header(self):
        try:
            # Make test csv file
            test_csv_file_path = os.path.join(self._args['datadir'], 'test.csv')
            with open(test_csv_file_path, 'w') as test_csv:
                writer = csv.writer(test_csv)
                writer.writerow([
                    'attributes',
                    'frame',
                    'strand',
                    'score',
                    'end',
                    'start',
                    'feature name',
                    'source',
                    'chrom'
                ])
                alphabet = 'ABCDEFGHI'
                for i in range(10):
                    attributes_string = 'genehancer_id=GH' + str(i)
                    for j in range(i):
                        attributes_string += ';connected_gene='
                        attributes_string += 'fakegene:' + alphabet[i-1] + '-' + alphabet[j] + ';'
                        attributes_string += 'score='
                        attributes_string += str(i) + '.' + str(j)
                    if i % 2 == 0:
                        attributes_string += ';'
                    writer.writerow([
                        attributes_string,
                        '.',
                        '.',
                        '0.' + str(i),
                        str(i) + '000',
                        str(i),
                        'Enhancer' + str(i),
                        'GeneHancer',
                        'chr' + str(i)
                    ])
            
            # Execute function that is being tested
            loader = NDExGeneHancerLoader(self._args)
            loader.__setattr__('_delimiter', ',')
            result_csv_file_path = loader._reformat_csv_file(test_csv_file_path, 
                                                             'test_csv_file',
                                                             'test_csv_file_name')

            # Check for correctness
            with open(result_csv_file_path, 'r') as result_csv:
                reader = csv.reader(result_csv, delimiter=',')
                i = 1
                j = 0
                for k, line in enumerate(reader):
                    if (k == 0):
                        expected_header = [
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
                        self.assertEqual(line, expected_header)
                    else:
                        expected_row = [
                            'GH' + str(i),
                            'p-genecards:GH' + str(i), 
                            'chr' + str(i),
                            str(i),
                            str(i) + '000',
                            '0.' + str(i),
                            'enhancer',
                            'Enhancer' + str(i),
                            'fakegene:' + alphabet[i-1] + '-' + alphabet[j],
                            'p-genecards:fakegene:' + alphabet[i-1] + '-' + alphabet[j],
                            str(i) + '.' + str(j),
                            'gene',
                            'Other gene'
                        ]
                        j += 1
                        if (j == i):
                            i += 1
                            j = 0
                        self.assertEqual(line, expected_row)
        except Exception as e:
            self.fail('Exception during test_reformat_csv_file ' + str(e))

    def test_get_gene_type(self):
        loader = NDExGeneHancerLoader(self._args)
        loader._gene_types = {
            'gene_types_gene' : 'gene_types_gene_type'
        }
        loader._internal_gene_types = {
            'internal_gene_types_gene' : 'internal_gene_types_gene_type'
        }

        self.assertEqual(
            loader._get_gene_type('gene_types_gene'), 
            'gene_types_gene_type')
        self.assertEqual(
            loader._get_gene_type('internal_gene_types_gene'), 
            'internal_gene_types_gene_type')

        self.assertEqual(loader._get_gene_type('LINC00649'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type('LOC105379194'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type('GC12M047038'), 'ncRNA gene')

        self.assertEqual(loader._get_gene_type('ENSG00000083622'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type('ENSG00000100101'), 'Protein coding gene')
        self.assertEqual(loader._get_gene_type('ENSG00000108516'), 'Other gene')

        self.assertEqual(loader._get_gene_type('PIR58695'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type('MIR6081'), 'ncRNA gene')

        self.assertEqual(loader._get_gene_type('not_a_gene'), 'Other gene')

        actual_internal_gene_types = loader._internal_gene_types
        expected_internal_gene_types = {
            'internal_gene_types_gene' : 'internal_gene_types_gene_type',
            'LINC00649' : 'ncRNA gene',
            'LOC105379194' : 'ncRNA gene',
            'GC12M047038' : 'ncRNA gene',
            'ENSG00000083622' : 'ncRNA gene',
            'ENSG00000100101' : 'Protein coding gene',
            'ENSG00000108516' : 'Other gene',
            'PIR58695' : 'ncRNA gene',
            'MIR6081' : 'ncRNA gene',
            'not_a_gene' : 'Other gene'
        }
        self.assertEqual(actual_internal_gene_types, expected_internal_gene_types)

    def test_get_gene_type_from_gene_info(self):
        loader = NDExGeneHancerLoader(self._args)
        
        self.assertEqual(loader._get_gene_type_from_gene_info('A1BG'), 'Protein coding gene')
        self.assertEqual(loader._get_gene_type_from_gene_info('AATBC'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type_from_gene_info('A2MP1'), 'Other gene')

        self.assertEqual(loader._get_gene_type_from_gene_info('ENSG00000111780'), 'Protein coding gene')
        self.assertEqual(loader._get_gene_type_from_gene_info('ENSG00000131484'), 'ncRNA gene')
        self.assertEqual(loader._get_gene_type_from_gene_info('ENSG00000230882'), 'Other gene')

        self.assertIsNone(loader._get_gene_type_from_gene_info('not_a_gene'))

    def test_update_gene_types(self):
        # Setup
        loader = NDExGeneHancerLoader(self._args)
        loader._gene_types = {}
        loader._internal_gene_types = {}
        
        # Do not update
        loader._update_gene_types = False
        loader._get_gene_type('B')
        self.assertTrue('B' in loader._internal_gene_types)
        self.assertFalse('B' in loader._gene_types)

        # Update
        loader._update_gene_types = True
        loader._get_gene_type('C')
        self.assertFalse('C' in loader._internal_gene_types)
        self.assertTrue('C' in loader._gene_types)

    def test_write_gene_type_to_file_cases(self):
        # Setup
        loader = NDExGeneHancerLoader(self._args)
        gene_types = {"gene": "type"}
        internal_gene_types = {"internal_gene": "internal_type"}
        gene_types_file = os.path.join(self._args['datadir'], 'types')

        # Update gene types, but gene types failed to load
        loader._update_gene_types = True
        loader._gene_types = None
        return_value = loader._write_gene_type_to_file('')
        self.assertIsNone(return_value)

        # Update gene types
        loader._gene_types = gene_types
        loader._gene_types_file = gene_types_file
        return_value = loader._write_gene_type_to_file('')
        self.assertEqual(gene_types_file, return_value)
        with open(gene_types_file, 'r') as gt:
            new_gene_types = json.load(gt)
        self.assertEqual(new_gene_types, gene_types)

        # Write new gene types, but there are none
        loader._update_gene_types = False
        loader._internal_gene_types = None
        return_value = loader._write_gene_type_to_file('')
        self.assertIsNone(return_value)

        # Write new gene types
        loader._data_directory = self._args['datadir']
        loader._internal_gene_types = internal_gene_types
        return_value = loader._write_gene_type_to_file('name')
        self.assertEqual(
            os.path.realpath(os.path.join(
                self._args['datadir'], 
                ndexloadgenehancer.GENE_TYPES_PREFIX + 'name.json')),
            return_value)
        with open(return_value, 'r') as gt:
            new_internal_gene_types = json.load(gt)
        self.assertEqual(new_internal_gene_types, internal_gene_types)

    def test_map_gene_type(self):
        loader = NDExGeneHancerLoader(self._args)

        self.assertEqual(loader._map_gene_type('protein-coding'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('protein_coding'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('IG_C_gene'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('IG_D_gene'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('IG_J_gene'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('IG_LV_gene'), 'Protein coding gene')
        self.assertEqual(loader._map_gene_type('IG_V_gene'), 'Protein coding gene')

        self.assertEqual(loader._map_gene_type('RNA'), 'ncRNA gene')
        self.assertEqual(loader._map_gene_type('anything_RNA'), 'ncRNA gene')
        self.assertEqual(loader._map_gene_type('ribozyme'), 'ncRNA gene')

        self.assertEqual(loader._map_gene_type('pseudo'), 'Other gene')
        self.assertEqual(loader._map_gene_type('anything_pseudo'), 'Other gene')
        self.assertEqual(loader._map_gene_type('pseudo_anything'), 'Other gene')
        self.assertEqual(loader._map_gene_type('anything_pseudo_anything'), 'Other gene')
        self.assertEqual(loader._map_gene_type('TEC'), 'Other gene')
        self.assertEqual(loader._map_gene_type('other'), 'Other gene')
        self.assertEqual(loader._map_gene_type('unknown'), 'Other gene')

        self.assertIsNone(loader._map_gene_type('not_a_gene_type'))

    def test_get_rep(self):
        loader = NDExGeneHancerLoader(self._args)
        self.assertEqual(loader._get_rep('GH01F220777'), ndexloadgenehancer.EN_GENECARDS + 'GH01F220777')
        self.assertEqual(loader._get_rep('other'), ndexloadgenehancer.P_GENECARDS + 'other')

    def test_generate_nice_cx_from_csv(self):
        loader = NDExGeneHancerLoader(self._args)

        # Check if _get_load_plan is being called
        try:
            with captured_output() as (out, err):
                loader._generate_nice_cx_from_csv('file')
            self.fail()
        except:
            self.assertIsNotNone(loader.__getattribute__('_load_plan'))

        # Check if network is being returned
        loader._load_plan = self._load_plan
        csv_file = os.path.join(self._args['datadir'], 'file.csv')
        with open(csv_file, 'w') as cf:
            writer = csv.writer(cf)
            writer.writerow(self._network_data_header)
            writer.writerows(self._network_data)
        try:
            network = loader._generate_nice_cx_from_csv(csv_file)
            self.assertIsInstance(network, ndex2.nice_cx_network.NiceCXNetwork)
        except:
            self.fail()
    
    def test_add_network_attributes(self):
        #Setup
        loader = NDExGeneHancerLoader(self._args)
        network_dataframe = pd.DataFrame(self._network_data, columns = self._network_data_header)
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(network_dataframe, self._load_plan)
        
        attributes = {
            "description": {
                "attribute": "new_description",
                "type": "string"
            },
            "reference": {
                "attribute": "new_reference"
            },
            "version": {
                "attribute": "1",
                "type": "double"
            },
            "networkType": {
                "attribute": [
                    "type1",
                    "type2"
                ],
                "type": "list_of_string"
            },
            "organism": {
                "attribute": [
                    1, 
                    2
                ],
                "type": "list_of_double"
            }
        }
        na_file = os.path.join(self._args['datadir'], 'attribs.json')
        with open(na_file, 'w') as f:
            json.dump(attributes, f, indent=4)

        loader.__setattr__('_network_attributes_file', na_file)
        loader._add_network_attributes(network, "network_name")

        # Test
        self.assertEqual(network.get_name(), 'network_name')
        expected_description = {
            'n': 'description',
            'v': 'new_description',
            'd': 'string'
        }
        self.assertEqual(network.get_network_attribute('description'), expected_description)
        expected_reference = {
            'n': 'reference',
            'v': 'new_reference',
            'd': 'string'
        }
        self.assertEqual(network.get_network_attribute('reference'), expected_reference)
        expected_version = {
            'n': 'version',
            'v': '1',
            'd': 'double'
        }
        self.assertEqual(network.get_network_attribute('version'), expected_version)
        expected_network_type = {
            'n': 'networkType',
            'v': ['type1', 'type2'],
            'd': 'list_of_string'
        }
        self.assertEqual(network.get_network_attribute('networkType'), expected_network_type)
        expected_organism = {
            'n': 'organism',
            'v': [1, 2],
            'd': 'list_of_double'
        }
        self.assertEqual(network.get_network_attribute('organism'), expected_organism)

        # Setup
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(network_dataframe, self._load_plan)

        attributes = {
            "name": {
                "attribute": "new_name",
                'type': 'double'
            },
            "prov:wasGeneratedBy": {
                'attribute': 'My version is {version}',
                'type': 'double'
            }
        }

        loader.__setattr__('_network_attributes', attributes)
        loader._add_network_attributes(network, 'network_name')
        
        # Test
        self.assertEqual(network.get_name(), 'new_name')
        expected_prov = {
            'n': 'prov:wasGeneratedBy',
            'v': 'My version is ' + str(ndexgenehancerloader.__version__),
            'd': 'string'
        }
        self.assertEqual(network.get_network_attribute('prov:wasGeneratedBy'), expected_prov)
        
    def test_add_network_style(self):
        loader = NDExGeneHancerLoader(self._args)
        network_dataframe = pd.DataFrame(self._network_data, columns = self._network_data_header)
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(network_dataframe, self._load_plan)
        
        # Check that _get_style_network is being called
        self.assertIsNone(loader._style_network)
        loader._add_network_style(network)
        self.assertIsNotNone(loader._style_network)

    def test_write_cx_to_file(self):
        loader = NDExGeneHancerLoader(self._args)
        ndexloadgenehancer._setup_logging(self._args)
        network_dataframe = pd.DataFrame(self._network_data, columns = self._network_data_header)
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(network_dataframe, self._load_plan)
        
        with captured_output() as (out, err):
            network_path = loader._write_cx_to_file(network, 'network_name')
        self.assertEqual(
            network_path, 
            os.path.realpath(
                os.path.join(
                    self._args['datadir'], 
                    ndexloadgenehancer.RESULT_PREFIX + 'network_name.cx')))

    def test_write_gene_type_to_file(self):
        gene_type = {
            'A': '1',
            'B': '2',
            'C': '3'
        }
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_internal_gene_types', gene_type)
        file_path = loader._write_gene_type_to_file('name')

        with open(file_path, 'r') as f:
            types = json.load(f)
            self.assertEqual(len(types), 3)
            self.assertEqual(types['A'], '1')
            self.assertEqual(types['B'], '2')
            self.assertEqual(types['C'], '3')

    def test_upload_cx(self):
        # Setup
        ndexloadgenehancer._setup_logging(self._args)
        loader = NDExGeneHancerLoader(self._args)
        network_dataframe = pd.DataFrame(self._network_data, columns = self._network_data_header)
        network = t2n.convert_pandas_to_nice_cx_with_load_plan(network_dataframe, self._load_plan)
        network.set_name('test')
        test_network_file = os.path.join(self._args['datadir'], 'test.cx')
        with captured_output() as (out, err):
            with open(test_network_file, 'w') as f:
                json.dump(network.to_cx(), f, indent=4)
        

        loader.__setattr__('_server', 'test_server')
        loader.__setattr__('_user', 'test_user')
        loader.__setattr__('_network_summaries', {})

        # Test exceptions
        with captured_output() as (out, err):
            loader._upload_cx(test_network_file, 'test')
        output = out.getvalue().strip().split('\n')
        output_1 = output[0].split('-')[3]
        output_2 = output[1].split('-')[3]
        self.assertEqual(
            output_1, 
            ' started uploading "test" on test_server for user test_user...')
        self.assertEqual(
            output_2,
            ' unable to update or upload "test" on test_server for user test_user')

        loader.__setattr__('_update_uuid', self._test_network_uuid)
        with captured_output() as (out, err):
            loader._upload_cx(test_network_file, 'test')
        output = out.getvalue().strip().split('\n')
        output_1 = output[0].split('-')[3]
        output_2 = output[1].split('-')[3]
        self.assertEqual(
            output_1, 
            ' started updating "test" on test_server for user test_user...')
        self.assertEqual(
            output_2,
            ' unable to update or upload "test" on test_server for user test_user')

        # Test updating network
        loader.__setattr__('_ndex', self._ndex_client)
        with captured_output() as (out, err):
            loader._upload_cx(test_network_file, 'test')
        output = out.getvalue().strip().split('\n')
        output_1 = output[0].split('-')[3]
        output_2 = output[1].split('-')[3]
        self.assertEqual(
            output_1, 
            ' started updating "test" on test_server for user test_user...')
        self.assertEqual(
            output_2,
            ' finished updating "test" on test_server for user test_user')

        # Test uploading new network
        network.set_name('delete_me')
        delete_network_file = os.path.join(self._args['datadir'], 'delete.cx')
        with captured_output() as (out, err):
            with open(delete_network_file, 'w') as f:
                json.dump(network.to_cx(), f, indent=4)

        loader.__setattr__('_update_uuid', None)
        with captured_output() as (out, err):
            loader._upload_cx(delete_network_file, 'delete_me')
        output = out.getvalue().strip().split('\n')
        output_1 = output[0].split('-')[3]
        output_2 = output[1].split('-')[3]
        self.assertEqual(
            output_1, 
            ' started uploading "delete_me" on test_server for user test_user...')
        self.assertEqual(
            output_2,
            ' finished uploading "delete_me" on test_server for user test_user')

        # Delete new network
        network_summaries = self._ndex_client.get_network_summaries_for_user(self._user)
        uuid = None
        for summary in network_summaries:
            if summary.get('name') == 'delete_me':
                uuid = summary.get('externalId')
                returnString = self._ndex_client.delete_network(uuid, retry=10)

    def test_run(self):
        pass
    def test_main(self):
        pass

    def test_parse_gene_types(self):
        # Setup
        genetypes = {
            "gene": "type"
        }
        gene_types_file = os.path.join(self._args['datadir'], 'types.json')
        with open(gene_types_file, 'w') as gt:
            json.dump(genetypes, gt, indent=4)

        # Input gene types file (do not update)
        args = {
            "genetypes": gene_types_file,
            "datadir": "dir"
        }
        args = dotdict(args)
        loader = NDExGeneHancerLoader(args)
        loader._get_gene_types()
        self.assertFalse(loader._update_gene_types)
        self.assertEqual(loader._gene_types_file, gene_types_file)
        self.assertEqual(loader._gene_types['gene'], 'type')

        # Default gene types file (do update)
        args = {
            "datadir": "dir"
        }
        args = dotdict(args)
        loader = NDExGeneHancerLoader(args)
        loader._get_gene_types()
        self.assertTrue(loader._update_gene_types)
        self.assertEqual(
            loader._gene_types_file, 
            ndexloadgenehancer._get_default_gene_types_name())

        # Input invalid gene types file (do update)
        args = {
            "genetypes": "",
            "datadir": "dir"
        }
        args = dotdict(args)
        loader = NDExGeneHancerLoader(args)
        with captured_output() as (out, err):
            loader._get_gene_types()
        self.assertEqual(
            out.getvalue().strip(),
            "[Errno 2] No such file or directory: ''\n"
            "Error while loading gene types. "
            "Default gene types will be used instead.")
        self.assertTrue(loader._update_gene_types)
        self.assertEqual(
            loader._gene_types_file, 
            ndexloadgenehancer._get_default_gene_types_name())

if __name__ == '__main__':
    unittest.main()