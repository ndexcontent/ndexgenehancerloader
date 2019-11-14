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




Python application that loads GeneHancer database to NDEx

This tool takes GeneHancer data in .xl* or .csv format and performs the following operations:

**1\)** GeneHancer data is converted to a csv file if necessary. (This produces a csv file with a name starting with "_intermediary" in the data directory.) 

**2\)** The "_intermediary" csv file is reformatted into a table containing network edges (details are below). (This produces a csv file with a name starting with "_result" in the data directory.)

**3\)** The "_result" csv file is transformed into a network. (This produces a cx file with a name starting with "_result" in the data directory.)

**4\)** The resulting network is uploaded to the NDEx account specified in the configuration file.

**5\)** The "_intermediary" and "_result" files are deleted from the data directory, unless the user specifies that they should be kept.

Reformating the Data
~~~~~~~~~~~~~~~~~~~~

The `original GeneHancer data <https://academic.oup.com/database/article/doi/10.1093/database/bax028/3737828>`_, which is a list of enhancers and the genes that they affect, contains 9 columns. 5 of these columns are used to transform the data into a network in the form of an edge table:

* **chrom**: The chromosome that the enhancer is found on (eg. chr2)
* **start**: The start location of the enhancer on the chromosome (eg. 70017801)
* **end**: The end location of the enhancer on the chromosome (eg. 70018000)
* **score**: The enhancer confidence score, which represents the strength of the evidence supporting the existence of the enhancer (eg. 0.52)
* **attributes**: A semi-colon delimited list of the enhancer's attributes, including:

  * **genehancer_id**: The enhancer's ID in the GeneCards database (eg. GH02F070017)
  * **connected_gene**: The name of a gene which the enhancer enhances (eg. PCBP1-AS1)
  * **score**: The gene-enhancer confidence score, which represents the strength of the evidence for a connection between the gene and the enhancer.
    
    For each enhancer, there can be multiple pairs of **connected_gene** and **score** attributes

In the resulting edge table, the source of each edge is a node representing the enhancer, and the target is a node representing the enhancer's connected gene. **Chrom**, **start**, **end**, and **score** (enhancer confidence score) are properties of the source node. **Score** (gene-enhancer confidence score) is a property of the edge between the nodes.

In addition to the properties above, most nodes also have an ID, and target nodes (genes) have a Gene Type. IDs consist of a prefix ("en-genecards" for enhancers and "p-genecards" for genes), a colon, and the name of the node. In NDEx, IDs serve as a link to the GeneCards entry for each gene and enhancer. Gene Type is a property of target nodes (genes) only, and can have one of three values:

* Protein coding gene
* ncRNA gene
* Other gene

These values are determined by the name of the gene, by examining the "genetypes.json" file which is available by default, or through a query on mygene.info. When the type of a gene cannot be determined in these ways, the Gene Type is set to "Other gene" by default.

+-------------------------+-----------------------------------------------+----------------------------------------------+
|                         | Name                                          | Properties                                   |
+=========================+===============================================+==============================================+
| Source node (enhancer)  | **genehancer_id**                             | * ID                                         |
|                         |                                               | * **chrom**                                  |
|                         |                                               | * **start**                                  |
|                         |                                               | * **end**                                    |
|                         |                                               | * **score** (enhancer confidence score)      |
+-------------------------+-----------------------------------------------+----------------------------------------------+
| Target node (gene)      | **connected_gene**                            | * ID                                         |
|                         |                                               | * Gene Type                                  |
+-------------------------+-----------------------------------------------+----------------------------------------------+
| Edge (enhancer to gene) | **genehancer_id** enhances **connected_gene** | * **score** (gene-enhancer confidence score) |
+-------------------------+-----------------------------------------------+----------------------------------------------+

Once the network is created, the following network attributes are set:

* **name** is set to the name of the original file that the data came from, not including the .xl* or .csv extension.
* **description** is set to:

  GeneHancer dataset <network name> uploaded as a cytoscape network.
    
    
* **reference** is set to:

  Fishilevich S, Nudel R, Rappaport N, et al. GeneHancer: genome-wide integration of enhancers and target genes in GeneCards. *Database (Oxford).* 2017;2017:bax028. `doi:10.1093/database/bax028 <http://doi.org/10.1093/database/bax028>`_

* **networkType** is set to ["interactome", "geneassociation"]
* **prov:wasGeneratedBy** is set to "ndexgenehancerloader 0.1.0"
* **prov:wasDerivedFrom** is set to "https://www.genecards.org/GeneHancer_version_4-4", which is the url that can be used to download GeneHancer data.
* **__iconurl** is set to "https://www.genecards.org/Images/Companions/Logo_GH.png", which is the url of the GeneHancer logo.

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
The default path for this configuration is :code:`~/.ndexutils.conf` but can be overridden with
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


Required files
------------

The original GeneHancer data (in .xl* or .csv format) must be present in the data directory (:code:`genehancer_data` by default) 


Usage
-----

For information invoke :code:`ndexloadgenehancer.py -h`

**Example usage**

This example assumes that there is a valid configuration file at :code:`~/.ndexutils.conf`, and that there is a directory called :code:`genehancer_data` in the current directory.

.. code-block::

   ndexloadgenehancer.py


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
.. _NDEx: http://www.ndexbio.org
