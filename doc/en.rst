SEPAL-MGCI
==========

Definition 
----------

The Mountain Green Cover Index (MGCI) is designed to measure the extent and the changes of green vegetation in mountain areas - i.e. forest, shrubs, trees, pasture land, cropland, etc. – in order to monitor progress towards the mountain target. MGCI is defined as the percentage of green cover over the total surface of the mountain region of a given country and for given reporting year. The aim of the index is to monitor the evolution of the green cover and thus assess the status of conservation of mountain ecosystems.

The SEPAL-MGCI module will allow you to calculate this index by following 4 steps that are described below. 

    
Requirements
------------

To run the MGCI SEPAL module you will need a web browser, an Internet connection, and a SEPAL and Google Earth Engine (GEE) account:

- SEPAL: is the enviroment where the module is deployed and therefore displayed. To create an account, please follow the `registration steps <https://docs.sepal.io/en/latest/setup/register.html#sign-up-to-sepal>`_ and then familiarize yourself with the tool by exploring its interface.
- GEE: the module has been built under the GEE Python API, which means that all the computational steps are done thorugh the GEE servers. Please follow the `registration steps <https://docs.sepal.io/en/latest/setup/gee.html#create-a-gee-account>`_ and `initialize the home folder <https://docs.sepal.io/en/latest/setup/gee.html#initialize-the-home-folder>`_.
- Connect your SEPAL and GEE accounts: the last step is to connect both accounts, you can achieve this by following the `step-by-step <https://docs.sepal.io/en/latest/setup/gee.html#connection-between-gee-and-sepal>`_.

SEPAL interface
---------------

If you are new to SEPAL, you would like to take a look over the interface and to familiarize with the main tools. A detalied description of the features can be consulted in the `interface documentation <https://docs.sepal.io/en/latest/setup/presentation.html#sepal-interface>`_. 

- Use the `apps tab <https://docs.sepal.io/en/latest/setup/presentation.html#apps-tab>`_ and navigate through the pages or type into the searchbox the "Mountain Green Cover Index" module. 

- Click over the app drawer and wait patiently until the the module is displayed in your session, which should be looks like the below image:


MGCI Module
-----------

A SEPAL module is divided into two main sections:

- Help drawers: used to describe the tool, objectives and give a background about how it was developed
    
  - About: 
  - Source code: the module was developed under a MIT licence, which means that the development is freely accesible and the code is public. It will link you to the GitHub repository of the module.
  - Wiki: 
  - Bug report: no tool is perfect and we are not exempt of bugs, furtunately, our team is always aware and constat alert to fix anything that is supposed to work well, so this section can be used to report any unexpected result or behaviour. To report an error please follow the `contribution guidelines <https://github.com/dfguerrerom/sepal_mgci/blob/master/CONTRIBUTE.md>`_.
  
- Process drawers: where you can find the steps or sections that are designed to be used for the used to accomplish the goal of the module. The MGCI module has therefore four main steps:

  - Area of interest selection
  - Mountain descriptor
  - Vegetation descriptor
  - MGCI results


Area of interest (AOI)
----------------------

The MGCI will be calculated based on the user inputs. The first mandatory input is the area of interest. In this step you'll have the possibility to choose from a predefined list of administrative layers or use your own datasets, the available options are:
 
- Predefined layers
   - Country/province
   - Administrative level 1 
   - Administrative level 2
- Custom layers
   - Vector file
   - Drawn shapes on map
   - Google Earth Engine Asset
   
After selecting the desired area, click over the 'Select these inputs' button and the map show up your selection.

.. note:: 

    You can only select one area of interest. In some cases, depending on the input data you could run out of resources in GEE.

.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/1_aoi_selection.PNG
   :align: center

Mountain descriptor layer 
-------------------------

Mountains can be defined with reference to a variety of parameters, such as climate, elevation, ecology (Körner et al., 2011) (Karagulle et al., 2017). This methodology adheres to the UNEP- WCMC mountain definition, relying in turn on the mountain description proposed by Kapos et al. (2000).
   
The global mountain descriptor layer is based on the mountain classification proposed by Kapos et al. (2000):

- Class 1: elevation > 4500 meters
- Class 2: elevation 3500 - 4500 meters
- Class 3: elevation 2500 – 3500 meters
- Class 4: elevation 1500 – 2500 meters and slope ≥ 2
- Class 5: elevation 1,000–1,500 meters and slope ≥ 5 or local elevation range (7 kilometers radius) ≥ 300 meters
- Class 6: elevation 300–1,000 meters and local elevation range (7 kilometres radius) ≥ 300 meters outside 23°N—19°S
- Class 0: Defined to represent the non-mountainous areas.

The mountain description layer used to derive the global estimates was created by the US Geological Survey from a 250 m DEM (Sayre et al. 2018)
These datasets may be replaced by nationally relevant data sources when available.

.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/2_mountain_descriptor.PNG
   :align: center

Vegetation descriptor layer
---------------------------

The vegetation descriptor layer categorizes land cover into green and non-green areas. Green vegetation includes both natural vegetation and vegetation resulting from anthropic activity (e.g. crops, afforestation, etc.). Non-green areas include very sparsely vegetated areas, bare land, water, permanent ice/snow and urban areas. The vegetation description layer can be derived in different ways, but remote sensing based land cover maps are the most convenient data source for this purpose, as they provide the required information on green and non-green areas in a spatially explicit manner and allow for comparison over time through land cover change analysis.

  
.. csv-table:: IPCC Classification!
   :header: "CODE", "Description", "Color"
   :widths: auto

   "1","Forest","#044D02"
   "2","Grassland","#F5FF00"
   "3","Cropland","#FF8100"
   "4","Wetland","#0013FF"
   "5","Settlement","#FFFFFF"
   "6","Other land","#FF00DE"
   
Reclassify assets
^^^^^^^^^^^^^^^^^

.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/3_1_reclassify_table.PNG
   :align: center
   
.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/3_3_vegetation_descriptor.PNG
   :align: center
   
Dashboard
---------

The module will calculate the area of every IPCC class into each Kapos range as well as the overall result.

..:warning: The module will only display the IPCC classes. The user has to reclassify the values from 1 to 6, otherwise the module will nest those classes into the "other lands" class (6). 

.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/4_dashboard_options.PNG
   :align: center
   
.. image:: https://raw.githubusercontent.com/dfguerrerom/sepal_mgci/master/doc/img/4_dashboard_results.PNG
   :align: center
