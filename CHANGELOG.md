## 0.4.0 (2023-12-17)

### Feat

- remove maps when values have changed
- improve time out computation
- improve error handling
- **tables**: rename and standarize transition table headers. - improve error handling
- **local_matrix**: copy transition matrix on local side

### Fix

- **legend**: set mountain legend on aoi map

### Refactor

- remove legacy code
- **biobelt**: increase max piexels

## 0.3.0 (2023-12-11)

### Feat

- use sepal_ui==2.17 to avoid conflicts with ipyleaflet
- rename results drawer
- align layer handler components
- add export as GDrive

### Fix

- fix layer handler broken event

### Refactor

- change TBD wording
- change degradation color palette
- **about**: add module documentation
- use sepal venv
- set sepal entry point
- **map_dashboard**: add B land cover layers
- enlarge dialog width
- **dash_map**: display readable layer names
- debug
- use custom legend
- typo

## 0.2.0 (2023-12-04)

### Feat

- add export dialog to export images
- set default height to aoi map
- give an unique name to the session
- add results map dashboard
- update about info
- add chips for sub_b
- update dashboard values
- set venv

### Refactor

- rename app
- **decorator**: drop debug param
- set sepal venv

## 0.1.0 (2023-11-27)

### Feat

- **tabs**: Add dark theme support to Tabs widget
- merge all tables into one export, apply styles to output
- set max-min-width
- set default data on sub_indicator_b inputs
- **alert**: fix multialert individual states
- **model.py**: define a default dem value to calculate rsa
- use set degradation values from 1 to 3
- function to plot degradation transition
- define transition degradation table
- modularize computation as independent script module
- refactor subindicator b years collection
- define test suite for reduced regions
- udpate uis
- versioning
- update deprecated pandas mehtod
- decorate settings buton on event. Add missin translation keys
- show default matrix for subindicator A as a dialog
- improve ui experience
- use BaseDialog on reclassify dialogs and validate file input on reclassify tile
- set alert as dialog
- add noxfile
- simplify aoi definitio
- use latest stable commit from sepal_ui
- create and use about tile as entry point to the app
- export results
- use virtual env
- allow and force headers for lc_classification file
- split dashboard for different indicators
- raise exception when there's no an aoi selected?
- add validation methods
- only calculate selected indicators
- remove unused files
- minor changes
- link transition matrix table with model. widget improvement
- define minimum requirements for custom transition matrix
- add second select widget to select belts in sub_b
- define custom inputs for sub_indicator b
- define workflow to export mountain area report
- add get_sub_b_years_labels fucntion
- **refactor**: add subindicator B dashboard:
- fully isolate CustomListB.
- adapt to latest scheme for table2 and table 3
- sankey plot
- sankey plot
- differenciate between sub a and b after computation
- differenciate between sub a and sub CustomLists
- set interpolation method for sub_indicator a
- get interpolation breaks
- tune of scripts to get years to calculate
- create alert for calculation contents
- use same year selecto for subB
- get dashboard tile independently
- name tile for easier access
- perform calculation with different indicators
- link reclassification asset with model
- link reclassify tables with model
- allow use custom target land cover classes
- separate Target Classes Dialog
- add typings to gitignore
- sepal_ui==2.16.0
- fix clear year inputs
- move to sepal_ui==2.15.2
- expansion panel
- adapt subindicator cards to match year of interest
- update to sepal_ui>2.15
- add components
- update no_ui
- add some keys
- add land cover transition matrix to the UI with questionarire
- set UI and concurrent workflow to faster calculation of subindicators
- UI for land cover transition impacts between years
- define calculation UI allowing select suba and subb
- create task msk icon widget to mutate within an alert
- set sub indicator a and b workflow
- functions to parse raw result and export results
- set new parameters
- new component keys
- add matrix and lulc_classes traits
- clean up
- new keys
- link selectable chips with dashboard display cards:
- add ic_items trait. It will be listened to populate selection cards
- link selection cards with model and dashboard cards
- embed indicator's into dialogs. Refactor dashboard
- set calculation tile
- set widgets to allow multiple calculatio dates
- create customizable legend control to display multiple variables
- get zonal statistics for bioclimatic belts and return json file
- refactor aoi view and tile to display bioclimatic belts
- add legend component
- scripts to retrieve and calculate new sdg 15.4.2 proposal
- reset the model if the mgci computation couldn't be completed
- run calculation in GEE background when is timed out. See: #30, #31
- change results dir, and closes #32
- make realsurfacearea off as default
- **reports**: closes #23 and therefore close #16
- force the use of an aoi
- remove process scale widget and calculate it based on the coarse input resolution, fix partially #16
- create a switch widget in dashboard to not/use the real sruface area
- only display the reclassified image within the kapos layer
- only display the reclassified image within the kapos layer
- create the display units as parameter, could be useful in some points #8.
- create the display units as parameter, could be useful in some points #8.
- create a custom questionaire. closes #18
- perfrom real surface area. closes #20
- define default map matrix and land use class asset id by default
- create description based on #15 and #10
- create a bool questionaire widget
- include 7th kapos class in the surrounding classes
- add gee workflow to calculate  7th kapos class
- add custom names to the aoi selector tile, fix partially #7 item 4
- include m49 code in the outputs, fix #13
- fix #12
- create a distitive output folder and fix minor typos
- create button to download outputs
- Workflow to create the summary output
- totally fix #4
- provide a default ipcc classification system
- create ipcc file for using defaults classification

### Fix

- add variable to all
- change default esa cci dataset, add custom dem to model
- use the geoareaname instead of code
- display only fao gaul contries that matches with m49. closes #7
- remove class 7 until we find a workaround
- use the finer scale. related to #30
- fix env in notebook
- debug
- typo
- change text, as requested by #16
- typos
- add imports
- add new constant to the all variable
- image borders
- typos
- fix mgci calculation
- typo

### Refactor

- clear
- calc drawer icon
- validation on selected sub_b
- **export**: sort tables
- **validation**: modularize validation step
- **reporting**: move export to calculation
- move message to end
- add vegetation tile
- remove legacy drawer
- update
- **sub_b**: improve subindicator b dashboard and report calculations
- create transition field on transition matrix
- outdated file
- rename gee calculations
- rename gee module
- **sub_b_calculation**: redone sub indicator B calculation
- **scripts**: reduce regions  modularizaion
- fix deprecation warnings from sepal_ui
- remove legacy button definition
- use base dialog
- fix typo
- display vegetation process as dialog
- typing
- move questionnaire from custom widgets and remove reclassify question
- clean leftover
- minor updates
- set schema for reporting tables
- change location of actions
- modify export report description text
- set scheme for sub indicator B
- clean leftoeveR:
- remove unused function and set typing definitions to functions
- remove and import functions from report_scripts
- move and merge getters that are used in reports scripts
- modify columns used for sub_a indicator and add cols for mountain area table
- use consistent header labels
- change workflow for breakpoints sub A
- simplify v_model from custom_list
- add vscode to gitignore
- minor clean up
- add expansion panels divided by subindicators
- remove unused params
- fallback to sepalui 2.14.2
- minor changes
- minor adaptation
- modify model workflow to adapt new indicator
- untrack new_indicator old files
- clean up imports, remove legacy code, minor changes
- return also feature collection id imgs and avoid multiple calls
- adapt vegetation tile with refactored reclassify widget
- link new reclassify component with indicator widgets
- change the way as the land cover classes are retrieved. now we're able to get from Image Collection instead of single images
- simplift reclassification tyle, doing specific calls to custom reclassification view
- remove legacy ui
- simplify reclassification widget, improvementes in UI/UX
- include  new parameters
- reclassify widget, making it simplier and improved UI/UX
- define transition and translation matrixes
- change translator message structure
- remove units, we"re always using sqkm, not anything else
- use else instead of rewrite
- **statistics-report**: refactor and re-allocate elements from the dasboard:
- **statistics-report**: refactor and re-allocate elements from the dasboard:
- adapt to the new reclassify model
- kapos class and real surface area
- kapos class and real surface area
- Create a new vegetation tile with a custom reclassify tile to fill the requeriments to close #15
- fix #18
- adapt ui to new components
- reallocate folders
- prevent loading multiple dashboards and rebuild tooltips due to the well known ipyvuetify bug, doc:add useful process messages.
- remove deprecated constants
- link useful reclassify model attributes with mgci_model (band as year, and the destination classes). Fix other elements.
- adapted to the new reclassification tile. The visualization are now done in the reclassification process.
- refactor elements by cleaning imports
