==============================
NDEx GeneHancer Content Loader
==============================


.. image:: https://img.shields.io/pypi/v/ndexgenehancerloader.svg
        :target: https://pypi.python.org/pypi/ndexgenehancerloader

.. image:: https://img.shields.io/travis/ceofy/ndexgenehancerloader.svg
        :target: https://travis-ci.org/ceofy/ndexgenehancerloader

.. image:: https://readthedocs.org/projects/ndexgenehancerloader/badge/?version=latest
        :target: https://ndexgenehancerloader.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status




Python application that loads the GeneHancer database to NDEx

This tool takes GeneHancer data in .xl*, tab separated, or comma separated format and performs the following operations:

**1\)** GeneHancer data is converted to a tsv file if it is an .xl* file. (This produces a tsv file with a name starting with "_intermediary_" in the data directory.) 

**2\)** The "_intermediary_" tsv file is reformatted into a table containing network edges (details are below). (This produces a *tsv* file with a name starting with "_result_" in the data directory.)

**3\)** The "_result_" tsv file is transformed into a network. (This produces a *cx* file with a name starting with "_result_" in the data directory.)

**4\)** The resulting network is uploaded to the NDEx account specified in the configuration file.

**5\)** The "_intermediary_" and "_result_" files are deleted from the data directory, unless the user specifies that they should be kept.

Reformating the Data
------------

`GeneHancer data <https://academic.oup.com/database/article/doi/10.1093/database/bax028/3737828>`_, which is a list of enhancers and the genes that they affect, contains 9 columns. 6 of these columns are used to transform the data into a network in the form of an edge table:

* **chrom**: The chromosome that the enhancer is found on (eg. chr2)
* **feature name**: The type of enhancer, either "Enhancer" or "Promoter/Enhancer"
* **start**: The start location of the enhancer on the chromosome (eg. 70017801)
* **end**: The end location of the enhancer on the chromosome (eg. 70018000)
* **score**: The enhancer confidence score, which represents the strength of the evidence supporting the existence of the enhancer (eg. 0.52)
* **attributes**: A semi-colon delimited list of the enhancer's attributes, including:

  * **genehancer_id**: The enhancer's ID in the GeneCards database (eg. GH02F070017)
  * **connected_gene**: The name of a gene which the enhancer enhances (eg. PCBP1-AS1)
  * **score**: The gene-enhancer confidence score, which represents the strength of the evidence for a connection between the gene and the enhancer.
    
    For each enhancer, there can be multiple pairs of **connected_gene** and **score** attributes

In the resulting edge table, the source of each edge is a node representing the enhancer, and the target is a node representing the enhancer's connected gene. **Chrom**, **start**, **end**, and **score** (enhancer confidence score) are properties of the source node. **Score** (gene-enhancer confidence score) is a property of the edge between the nodes.

In addition to the properties above, nodes also have an ID, source nodes (enhancers) have an Enhancer Type, and target nodes (genes) have a Gene Type. IDs consist of a prefix ("en-genecards" for enhancers and "p-genecards" for genes), a colon, and the name of the node. In NDEx, IDs serve as a link to the GeneCards entry for each gene and enhancer. Enhancer Type is a property of source nodes (enhancers) only, and can have one of two values:

* Enhancer
* Promoter/Enhancer

Gene Type is a property of target nodes (genes) only, and can have one of three values:

* Protein coding gene
* ncRNA gene
* Other gene

The Gene Type values are determined by parsing the name of the gene, by examining the "genetypes.json" file which is available by default, or through a query on mygene.info. When the type of a gene cannot be determined in these ways, the Gene Type is set to "Other gene" by default.

+-------------------------+-----------------------------------------------+------------------------------------------------------------------+
|                         | Name                                          | Properties                                                       |
+=========================+===============================================+==================================================================+
| Source node (enhancer)  | **genehancer_id**                             | * ID: en-genehancer:**genehancer_id**                            |
|                         |                                               | * Chromosome: **chrom**                                          |
|                         |                                               | * EnhancerType: **feature name**                                 |
|                         |                                               | * StartLocation: **start**                                       |
|                         |                                               | * EndLocation: **end**                                           |
|                         |                                               | * EnhancerConfidenceScore: **score** (enhancer confidence score) |
+-------------------------+-----------------------------------------------+------------------------------------------------------------------+
| Target node (gene)      | **connected_gene**                            | * ID: p-genehancer:**connected_gene**                            |
|                         |                                               | * GeneType: Gene Type                                            |
+-------------------------+-----------------------------------------------+------------------------------------------------------------------+
| Edge (enhancer to gene) | **genehancer_id** enhances **connected_gene** | * GeneEnhancerScore: **score** (gene-enhancer confidence score)  |
+-------------------------+-----------------------------------------------+------------------------------------------------------------------+

Once the network is created, the following network attributes are set by default:

* **name** is set to "GeneHancer Associations.
* **description** is set to:

  `GeneHancer <https://www.genecards.org/Guide/GeneCard#enhancers>`_ is a database of genome-wide enhancer-to-gene and promoter-to-gene associations, embedded in GeneCards, with regulatory elements mined from several sources.
  Free for academic non-profit institutions. Other users need a `Commercial license <http://www.lifemapsc.com/contact-us/>`_.
  - Enhancers are represented by orange octagons and their size is proportional to the "EnhancerConfidenceScore" value.
  - Protein-coding genes are represented by rectangles with a blue border, RNA genes have a purple border while other genes have grey borders as described in the `original paper <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5467550/>`_.
  - Edge width is maped to the "GeneHancerScore" value.
    
* **reference** is set to:

  Fishilevich S, Nudel R, Rappaport N, et al. GeneHancer: genome-wide integration of enhancers and target genes in GeneCards. *Database (Oxford).* 2017;2017:bax028. `doi:10.1093/database/bax028 <http://doi.org/10.1093/database/bax028>`_

* **networkType** is set to ["interactome", "geneassociation"]

* **organism** is set to "Human, 9606, Homo sapiens"

* **rights** is set to `Free for academic non-profit institutions. Other users need a Commercial license. <http://www.lifemapsc.com/contact-us/>`_
  
* **rightsHolder** is set to "LifeMap Sciences"

* **prov:wasGeneratedBy** is set to "ndexgenehancerloader 1.0.0"

* **__iconurl** is set to "https://www.genecards.org/Images/Companions/Logo_GH.png", which is the url of the GeneHancer logo.

A different set of network attributes can be set using the --networkattributes option.

Dependencies
------------

* `ndex2 <https://pypi.org/project/ndex2>`_
* `ndexutil <https://pypi.org/project/ndexutil>`_
* `mygene <https://pypi.org/project/mygene/>`_
* `pandas <https://pypi.org/project/pandas/>`_
* `xlrd <https://pypi.org/project/xlrd/>`_

Compatibility
-------------

* Python 3.3+

Installation
------------

.. code-block::

   git clone https://github.com/ceofy/ndexgenehancerloader
   cd ndexgenehancerloader
   make dist
   pip install dist/ndexloadgenehancer*whl


Configuration
-------------

The **ndexloadgenehancer.py** requires a configuration file in the following format be created.
The default path for this configuration is :code:`/.ndexutils.conf` but can be overridden with
:code:`--conf` flag.

**Format of configuration file**

.. code-block::

    [<value in --profile (default ndexgenehancerloader)>]

    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server(omit http) ie public.ndexbio.org>

**Example configuration file**

.. code-block::

    [ndexgenehancerloader]
    user = joe123
    password = somepassword123
    server = dev.ndexbio.org
    
Optionally, a profile containing the credentials to access a network whose style should be copied into the uploading network can also be specified.

**Format of configuration file with second profile for style**

.. code-block::

    [<value in --profile (default ndexgenehancerloader)>]
    
    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server(omit http) ie public.ndexbio.org>
    
    [<value in --styleprofile>]
    
    user = <NDEx username>
    password = <NDEx password>
    server = <NDEx server>
    uuid = <UUID of network that should be used for style>
    
**Example configuration file with second profile for style**

.. code-block::

    [ndexgenehancerloader]
    
    user = joe123
    password = somepassword123
    server = dev.ndexbio.org
    
    [style]
    
    user = jane123
    password = someotherpassword123
    server = ndexbio.org
    uuid = 00000000-0000-0000-0000-000000000000

Required files
------------

**GeneHancer Data**

A file containing GeneHancer data (in .xl*, comma separated, or tab separated format) must be present in the data directory (:code:`genehancer_data` by default). **Ensure that there are no other files not produced by this script in the data directory**, as the script is designed to upload one network at a time.

**Configuration**

A configuration file (see above) must also be present, either at ~/.ndexutils.conf or at a location specified by the --conf option.

Useful files
------------

**Network Attributes**

This file determines the attributes (name, description, etc.) that will be applied to the network.

A default network attributes file (networkattributes.json) is provided, but optionally a different file containing different attributes can be specified using the --networkattributes option.

The network attributes file should be formatted as follows:

.. code-block::
    
    {
        "attributes": [
            {
                "n": "<name of attribute>",
                "v": "<value of attribute>",
                "d": "<data type of attribute>"
            },
            {
                "n": "<name of attribute>",
                "v": "<value of attribute>",
                "d": "<data type of attribute>"
            },
            etc . . .
        ]
    }
    
**Gene Types**

This file provides the script with a list of the gene types (Protein coding gene, ncRNA gene, Other gene) of known genes. Having a complete or near complete list of gene types significantly increases the speed of the program (a large network can take several hours to load otherwise).

A default gene types file (genetypes.json) is provided, but optionally a different file containing updated or more accurate gene types can be specified using the --genetypes option.

The gene types file should be formatted as follows:

.. code-block::
    
    {
        "<gene>": "<gene type>",
        "<gene>": "<gene type>",
        etc . . .
    }
    
**Load Plan**

This file gives instructions for mapping columns of the "_results_" tsv document to node and edge properties in the network.

A default load plan (loadplan.json) is provided, but optionally a different file containing a different load plan can be specified using the --loadplan option.

The load plan must validate against `this json schema <https://github.com/ndexbio/ndexutils/blob/master/ndexutil/tsv/loading_plan_schema.json>`_.

Usage
-----

For information invoke :code:`ndexloadgenehancer.py -h`

**Example 1**

This example assumes that there is a valid configuration file at :code:`~/.ndexutils.conf`, and that there is a directory called :code:`genehancer_data` in the current directory.

.. code-block::

   ndexloadgenehancer.py
   
**Example 2**

This example will update the network at the uuid <uuid> with the new version number <version>, using the data in the directory <data directory>, using tabs as a delimiter. It will do this without changing the visibility of the network, the uuid, or any network attributes besides the version number. It will also keep all intermediary files created during the loading process, which can be useful in case the loading fails at a late stage. 

.. code-block::
    
    ndexloadgenehancer.py --datadir <data directory> --update <uuid> --version <version> --nocleanup

Options
-------

+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| Option              | Function                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         | Example                                                                                    |
+=====================+==================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================+============================================================================================+
| --help              | Shows the help message and exits the program.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | --help, -h                                                                                 |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --datadir           | Sets the directory that the input data is found in. Any files created by the script will also be in this directory. (Default: genehancer_data)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | --datadir <Directory name>                                                                 |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --update            | Sets the uuid of the network that is going to be updated by the script. Updating a network replaces its nodes and edges, but not its network attributes or style, unless the --networkattributes, --version, --stylefile, or --styleprofile options are used. (No default)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | --update <UUID>, --updateuuid <UUID>                                                       |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --version           | Sets the version number of the network being created. The resulting network will have an attribute called “version” which is equal to the value passed in to this option. (No default)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | --version <version>, --versionnumber <version>                                             |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --loadplan          | Sets the file containing the load plan that should be used to create the network. The load plan is a json document that must validate against `this schema <https://github.com/ndexbio/ndexutils/blob/master/ndexutil/tsv/loading_plan_schema.json>`_. (Default: loadplan.json)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | --loadplan <loadplan file>                                                                 |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --stylefile         | Sets the file containing the network (in .cx format) whose style should be applied to the new network. (Default: style.cx)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       | --stylefile <style file>                                                                   |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --conf              | Sets the file containing the configuration file to use. This file contains the NDEx credentials necessary to upload a network to an NDEx account. (Default: ~/.ndexutils.conf)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | --conf <configuration file>                                                                |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --profile           | Sets the name of the profile to use from the configuration file. (Default: ndexgenehancerloader)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | --profile <name of profile>                                                                |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --styleprofile      | Sets the name of the profile to use to access a network on NDEx whose style should be applied to the new network. (No default)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   | --styleprofile <name of style profile>                                                     |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --genetypes         | Sets the name of the file containing the types of genes. This file should be a json document containing an object where each key is a gene name and each corresponding value is a gene type (one of “Protein coding gene”, “ncRNA gene”, or “Other gene”). (Default: genetypes.json)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | --genetypes <name of gene types file>                                                      |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --networkattributes | Sets the name of the file containing the attributes that should be applied to the network being made. Note that using this option will override any attributes that the network previously had. The network attributes file should contain a json object with a key "attributes", which corresponds to a list. This list should be a list of json objects, where each object has the keys "n", "v", and optionally "d". The value of "n" should be the `attribute's name <https://docs.google.com/document/d/1Te2MpVXrFDqKK5GsE3aTvhVZM5KtUlthEf1uvsIa3PE/edit#bookmark=id.fhf1313hmkvc>`_ (eg. "organism"), the value of "v" should be the attribute's value (eg. "Homo sapiens"), and the value of "d" should be the `data type <https://docs.google.com/document/d/1Te2MpVXrFDqKK5GsE3aTvhVZM5KtUlthEf1uvsIa3PE/edit#bookmark=id.dg6bqwesr0fv>`_ of the attribute's value (eg. "list_of_string"). If "d" is not present, it will be assumed that the data type is "string". (Default: networkattributes.json) | --networkattributes <name of network attributes file>                                      |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --delimiter         | Sets the delimiter that should be used to parse the input data file. If this option is not specified, the script will try to guess the correct delimiter based on the file extension. A .csv file will set the delimiter to a comma by default. Any other file will set it to a tab by default. (Default: comma for .csv file, tab otherwise)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    | --delimiter <delimiter>                                                                    |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --logconf           | Sets the file containing the logging configuration to use. The logging configuration should be in `this format <https://docs.python.org/3/library/logging.config.html#logging-config-fileformat>`_. Setting this option overrides the --verbose option. (No default)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             | --logconf <logging configuration file>                                                     |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --verbose           | Sets the verbosity of the logging to standard error in this module and in the ndexutil.tsv.tsv2nicecx2 module. Messages are output at these python logging levels: -verbose or -v = ERROR, -vv = WARNING, -vvv = INFO, -vvvv = DEBUG, -vvvvv = NOTSET. (Default: no logging)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     | -verbose, -v, -vv, -vvv, -vvvv, -vvvvv                                                     |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --noheader          | Tells the script that the input data has no header. In this case, a default header will be used.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 | --noheader                                                                                 |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| --nocleanup         | Tells the script not to remove any files generated during the loading process. This may include a “_intermediary_” tsv file if the input was an xl file, a “_result_” tsv file containing an edge list, a “_result_” cx file containing the final network in cx format, and a “_genetypes_” json file containing the gene types that were retrieved using the mygene api. Passing the “_genetypes_” file in to the --genetypes option may significantly speed up the loading process.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | --nocleanup                                                                                |
+---------------------+------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _NDEx: http://www.ndexbio.org
