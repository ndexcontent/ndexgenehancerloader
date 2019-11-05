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
from StringIO import StringIO

from ndexutil.config import NDExUtilConfig
import ndexgenehancerloader
from ndexgenehancerloader import ndexloadgenehancer
from ndexgenehancerloader.ndexloadgenehancer import NDExGeneHancerLoader
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
            'conf': None,
            'loadplan': None,
            'style': None,
            'profile': None,
            'logconf': None,
            'verbose': None,
            'noheader': None,
            'nocleanup': None
        }
        self._args = dotdict(self._args)
        self._user = 'sophieTest'
        self._password = 'test12345'
        self._server = 'dev.ndexbio.org'
        self._test_network_uuid = 'dcf9392c-ff39-11e9-93e0-525400c25d22'

        self._ndex_client = Ndex2(host=self._server, 
                                  username=self._user,
                                  password=self._password)

    def tearDown(self):
        """Tear down test fixtures, if any"""
        if os.path.exists(self._args['datadir']):
            shutil.rmtree(self._args['datadir'])

    def testget_package_dir(self):
        actual_package_dir = ndexloadgenehancer.get_package_dir()
        expected_package_dir = os.path.dirname(ndexgenehancerloader.__file__)
        self.assertEqual(actual_package_dir, expected_package_dir)

    def test_get_default_datadir_name(self):
        actual_datadir = ndexloadgenehancer._get_default_data_dir_name()
        expected_datadir = ndexloadgenehancer.DATA_DIR
        self.assertEqual(actual_datadir, expected_datadir)

    def test_get_default_load_plan_name(self):
        actual_load_plan = ndexloadgenehancer._get_default_load_plan_name()
        expected_load_plan = os.path.join(ndexloadgenehancer.get_package_dir(), ndexloadgenehancer.LOAD_PLAN)
        self.assertEqual(actual_load_plan, expected_load_plan)

    def test_get_default_style_name(self):
        actual_style = ndexloadgenehancer._get_default_style_name()
        expected_style = os.path.join(ndexloadgenehancer.get_package_dir(), ndexloadgenehancer.STYLE)
        self.assertEqual(actual_style, expected_style)

    def test_get_default_configuration_name(self):
        actual_config = ndexloadgenehancer._get_default_configuration_name()
        expected_config = os.path.join('~/', NDExUtilConfig.CONFIG_FILE)
        self.assertEqual(actual_config, expected_config)

    def test_parse_arguments(self):
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
        expected_default_args['datadir'] = 'genehancer_data'
        expected_default_args['conf'] = '~/.ndexutils.conf'
        expected_default_args['loadplan'] = ndexloadgenehancer._get_default_load_plan_name()
        expected_default_args['style'] = ndexloadgenehancer._get_default_style_name()
        expected_default_args['profile'] = 'ndexgenehancerloader'
        expected_default_args['logconf'] = None
        expected_default_args['verbose'] = 0
        expected_default_args['noheader'] = False
        expected_default_args['nocleanup'] = False

        default_args = ndexloadgenehancer._parse_arguments(desc, args)
        self.assertDictEqual(default_args.__dict__, expected_default_args)

        #Test new args
        args.append('--datadir')
        args.append('new_dir')
        args.append('--conf')
        args.append('new_conf')
        args.append('--loadplan')
        args.append('new_load_plan')
        args.append('--style')
        args.append('new_style')
        args.append('--profile')
        args.append('new_profile')
        args.append('--logconf')
        args.append('new_log_conf')
        args.append('--verbose')
        args.append('--noheader')
        args.append('--nocleanup')

        expected_args = {}
        expected_args['datadir'] = 'new_dir'
        expected_args['conf'] = 'new_conf'
        expected_args['loadplan'] = 'new_load_plan'
        expected_args['style'] = 'new_style'
        expected_args['profile'] = 'new_profile'
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

    def test_parse_config(self):
        temp_dir = self._args['datadir']
        try:
            p = Param()
            self._args['profile'] = 'test_conf_section'
            self._args['conf'] = os.path.join(temp_dir, 'temp.conf')

            with open(self._args['conf'], 'w') as f:
                f.write('[' + self._args['profile'] + ']' + '\n')
                f.write(NDExUtilConfig.USER + ' = aaa\n')
                f.write(NDExUtilConfig.PASSWORD + ' = bbb\n')
                f.write(NDExUtilConfig.SERVER + ' = dev.ndexbio.org\n')
                f.flush()

            loader = NDExGeneHancerLoader(self._args)
            loader._parse_config()
            self.assertEqual('aaa', loader._user)
            self.assertEqual('bbb', loader._pass)
            self.assertEqual('dev.ndexbio.org', loader._server)
        finally:
            shutil.rmtree(temp_dir)

    def test_get_file_path(self):
        loader = NDExGeneHancerLoader(self._args)
        actual_file_path = loader._get_file_path('file')
        expected_file_path = os.path.join(loader._data_directory, 'file')
        self.assertEqual(actual_file_path, expected_file_path)
    
    #def test_get_load_plan(self):
        
    #def test_get_template_network(self):

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

    #def test_convert_from_xl_to_csv(self):

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

    @unittest.skip("Skipping until test account is settled")
    def test_load_network_summaries_for_user(self):
        loader = NDExGeneHancerLoader(self._args)

        loader.__setattr__('_server', self._server)
        loader.__setattr__('_user', self._user)
        loader.__setattr__('_pass', self._password)
        loader.__setattr__('_ndex', loader._create_ndex_connection())

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
            "TEST" : "6f967342-fd07-11e9-93e0-525400c25d22"
        }

        actual_summaries = loader.__getattribute__('_network_summaries')
        self.assertEqual(actual_summaries, expected_summaries)
        
    def test_reformat_csv_file(self):
        try:
            # Make test csv file
            test_csv_file_path = os.path.join(self._args['datadir'], 'test.csv')
            with open(test_csv_file_path, 'w') as test_csv:
                writer = csv.writer(test_csv)
                writer.writerow([
                    'chrom',
                    'source',
                    'feature name',
                    'start',
                    'end',
                    'score',
                    'strand',
                    'frame',
                    'attributes'
                ])
                alphabet = 'ABCDEFGHI'
                for i in range(10):
                    attributes_string = 'genehancer_id=GH' + str(i)
                    for j in range(i):
                        attributes_string += ';connected_gene='
                        attributes_string += alphabet[i-1] + '-' + alphabet[j] + ';'
                        attributes_string += 'score='
                        attributes_string += str(i) + '.' + str(j)
                    if i % 2 == 0:
                        attributes_string += ';'
                    writer.writerow([
                        'chr' + str(i),
                        'GeneHancer',
                        'Enhancer',
                        str(i),
                        str(i) + '000',
                        '0.' + str(i),
                        '.',
                        '.',
                        attributes_string
                    ])
            
            # Execute function that is being tested
            loader = NDExGeneHancerLoader(self._args)
            result_csv_file_path = loader._reformat_csv_file(test_csv_file_path, 
                                                             'test_csv_file')

            # Check for correctness
            with open(result_csv_file_path, 'r') as result_csv:
                reader = csv.reader(result_csv, delimiter=',')
                i = 1
                j = 0
                for k, line in enumerate(reader):
                    if (k == 0):
                        expected_header = [
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
                        self.assertEqual(line, expected_header)
                    else:
                        expected_row = [
                            'GH' + str(i),
                            'chr' + str(i),
                            str(i),
                            str(i) + '000',
                            '0.' + str(i),
                            'enhancer',
                            alphabet[i-1] + '-' + alphabet[j],
                            'hgnc:' + alphabet[i-1] + '-' + alphabet[j],
                            str(i) + '.' + str(j),
                            'gene'
                        ]
                        j += 1
                        if (j == i):
                            i += 1
                            j = 0
                        self.assertEqual(line, expected_row)
        except Exception as e:
            self.fail('Exception during test_reformat_csv_file ' + str(e))
            if os.path.exists(test_csv_file_path):
                print('test_csv_file_path exists')
                os.remove(test_csv_file_path)
            if os.path.exists(result_csv_file_path):
                print('result_csv_file_path exists')
                os.remove(result_csv_file_path)
        finally:
            # Delete files created
            os.remove(test_csv_file_path)
            os.remove(result_csv_file_path)


    """
    def test_generate_nice_cx_from_csv(self):
        try:
            # Make test csv file
            test_csv_file_path = os.path.join(self._args['datadir'], 'test.csv')
            with open(test_csv_file_path, 'w') as test_csv:
                writer = csv.writer(test_csv)
                writer.writerow([
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
                ])
                alphabet = 'ABCDEFGHI'
                i = 1
                j = 0
                while i < 10 and j < i:
                    writer.writerow([
                        'GH' + str(i),
                        'chr' + str(i),
                        str(i),
                        str(i) + '000',
                        '0.' + str(i),
                        'enhancer',
                        alphabet[i-1] + '-' + alphabet[j],
                        alphabet[i-1] + '-' + alphabet[j],
                        str(i) + '.' + str(j),
                        'protein'
                    ])
                    j += 1
                    if (j == i):
                        i += 1
                        j = 0

            # Execute function that is being tested
            loader = NDExGeneHancerLoader(self._args)
            loader.__setattr__('_load_plan', 
                               ndexloadgenehancer._get_default_load_plan_name())
            actual_network_nice_cx = loader._generate_nice_CX_from_csv(
                test_csv_file_path,
                loader._get_load_plan())
            actual_network = actual_network_nice_cx.to_cx()

            print(actual_network)

            # Test for correctness
            
            expected_network_stream = self._ndex_client.get_network_as_cx_stream(
                self._test_network_uuid)
            expected_network_string = ''
            for item in expected_network_stream:
                expected_network_string += str(item)
            expected_network = json.loads(expected_network_string)

            print('\n\n\n')
            print(expected_network_string)
            print('\n\n\n')
            print(expected_network)
            self.assertEqual(actual_network, expected_network)

        except Exception as e:
            self.fail("Failed during test_generate_nice_cx " + str(e))
            if os.path.exists(test_csv_file_path):
                print('test_csv_file_path exists')
                os.remove(test_csv_file_path)
        finally:
            # Delete files created
            os.remove(test_csv_file_path)
    """


    #def test_add_network_attributes(self):

    #def test_add_network_style(self):

    #def test_write_cx_to_file(self):

    def test_upload_cx(self):
        # Set up loader
        loader = NDExGeneHancerLoader(self._args)
        loader.__setattr__('_user', 'test_user')
        loader.__setattr__('_server', 'test_server')
        loader.__setattr__('_ndex', self._ndex_client)
        loader.__setattr__('_network_summaries', {})
     
        # Download test cx file
        test_cx_stream = self._ndex_client.get_network_as_cx_stream(
            self._test_network_uuid)
        test_cx_string = ''
        for item in test_cx_stream:
            test_cx_string += item
        test_cx_file_path = os.path.join(self._args['datadir'], 'test.cx')
        with open(test_cx_file_path, 'w') as f:
            json.dump(test_cx_string, f, indent=4)
    
        #Test uploading
        with captured_output() as (out, err):
            return_code = loader._upload_cx(test_cx_file_path, 'test')
            output = out.getvalue().strip()

        self.assertEquals(return_code, 0)
        
        lines = output.split('\n')
        self.assertEquals(len(lines), 2)

        for i in range(len(lines)):
            line = lines[i].split('-')
            self.assertEquals(len(line), 4)
            if i == 0:
                self.assertEquals(
                    ' started uploading "test" on test_server for user test_user...',
                    line[3])
            else:
                self.assertEquals(
                    ' finished uploading "test" on test_server for user test_user',
                    line[3]
                )
        
        #Test updating
        loader.__setattr__('_network_summaries', {'TEST': self._test_network_uuid})
        with captured_output() as (out, err):
            return_code = loader._upload_cx(test_cx_file_path, 'test')
            output = out.getvalue().strip()
        
        self.assertEquals(return_code, 0)
        
        lines = output.split('\n')
        self.assertEquals(len(lines), 2)

        for i in range(len(lines)):
            line = lines[i].split('-')
            self.assertEquals(len(line), 4)
            if i == 0:
                self.assertEquals(
                    ' started updating "test" on test_server for user test_user...',
                    line[3])
            else:
                self.assertEquals(
                    ' finished updating "test" on test_server for user test_user',
                    line[3]
                )

        #Test unable to update or upload
        loader.__setattr__('_ndex', None)
        with captured_output() as (out, err):
            return_code = loader._upload_cx(test_cx_file_path, 'test')
            output = out.getvalue().strip()

        self.assertEquals(return_code, 2)

    #Download test cx
    #Upload, check that it's updating
    #Change name
    #Upload, check that it's uploading
    #Delete uploaded network


        

if __name__ == '__main__':
    unittest.main()