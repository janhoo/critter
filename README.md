
<img src="./shiny/www/crabbybanner.png" alt="Critter Logo" width=210/>




## Overview
Critter is a comprehensive data management solution to essentially replace the previous system of spreadsheets and repositories in ubiquitous use. The idea is to achieve sufficient long-term robustness, openness, accessibility and coherence to permit comprehensive exploitation by both modern Web technologies and ongoing "classical" research.

Main Goals:
1. Provide a consistent data model
  * Enable coherent interrogation of data sets
  * Achieve reproducibility and reusability of research results
  * Data accessibility for humans and machines (realizing programmatic machine actionability of cited data)
2. Provide tools for data ingest and manipulation
  * Check data plausibility
  * Enforce data standards
3. Provide a web-based data exploration and retrieval tool
  * User driven design
  * Modular architecture



The **critter** framework consists of the three modules (i) database, (ii) ingest and curation tool, and (iii) visualization and retrieval tool. Take a look at [this poster](https://zenodo.org/record/1146361/files/critter_poster_arcticchange2017_holstein.pdf) for rationale and background information.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1153984.svg)](https://doi.org/10.5281/zenodo.1153984)  **Conference Presentation**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146361.svg)](https://doi.org/10.5281/zenodo.1146361)   **Poster**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146542.svg)](https://doi.org/10.5281/zenodo.1146542)   **Visualization tool**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146533.svg)](https://doi.org/10.5281/zenodo.1146533)    **Ingest tool**

[![Inline docs](http://inch-ci.org/github/dwyl/hapi-auth-jwt2.svg?branch=master)](https://janhoo.github.io/critter/)    **Data model**

Based on an elaborated, but still simple enough [data model](https://janhoo.github.io/critter/) , the operational data base is the framework's centerpiece which allows concise and coherent data interrogation and building sustainable services for data, visualization, or story telling of top of it.

To help researchers with data ingestion and curation, an ingest tool provides a graphical user interface from where standard operations are performed. The visualization and retrieval tool is a  web-based prototype built to showcase visualization techniques and to enable user-driver demand analysis is currently under evaluation in the ESKP-project [RoaStBiW](https://www.researchgate.net/project/RoaStBiW) with several stakeholders. You can check it out on [janhoo.shinyapps.io](https://janhoo.shinyapps.io/arcticcritter/) or use the function `runGitHub()` to run it locally



```
if (!require('shiny')) install.packages("shiny")
if (!require('plyr')) install.packages("shiny")
if (!require('dplyr')) install.packages("shiny")
if (!require('rlang')) install.packages("shiny")
if (!require('leaflet')) install.packages("shiny")
if (!require('googleVis')) install.packages("googleVis")
if (!require('xtable')) install.packages("shiny")
if (!require('RcolorBrewer')) install.packages("shiny")
shiny::runGitHub("critter", "janhoo", subdir = "shiny")
```



## Installation

### Prerequisites for the full framework
* PostgreSQL 9.x
* python3 including pyqt5, xlsxwriter, psycopg2, folium

additionally for development
* R version 3.4.x
* QT5 Designer

1. install postgreSQL 9.x
2. then set up the database
```
cat critterbase/db.ddl.sql | psql -d <YOURDATABASENAME> -U <YOURDBUSER> -h <YOURHOSTe.g.localhost> -p <PORTe.g.5432> -q
```
3. install python3 and the dependencies.
```
./ingesttool/multiplatform/install_dependencies_<YOUROS>.sh
```
Windows user pls take a look at `./ingesttool/multiplatform/install_dependencies_win.txt`



## Getting started

- [x] Feel embarrassed because this section is a massive void
- [ ] Provide example data
- [ ] show how to use the ingest tool to connect to the database
- [ ] show how to use the ingest tool to produce template .csv files
- [ ] show how to use the ingest tool to ingest the example data
- [ ] show how to use the ingest tool to perform basic database operations
- [ ] show how to use the ingest tool to add root data to look-up-tables
- [ ] explain some basic assumptions and principles of the data model
- [ ] show how to connect the visualization to the database
- [ ] show how to properly cite data retrieved with the visualization tool


## Contact
* submit suggestions and bug-reports at: https://github.com/janhoo/benthos/issues
* send a pull request on: https://github.com/janhoo/benthos/
* compose a friendly e-mail to:janmholstein[at]gmail(dot)com

## Authors

* Jan Holstein - Data Model, Concept, Architecture & Programming
* Paul Kloss & Jan Holstein - Ingest Tool

## Terms of use
This work is owned by Jan Holstein and partly by Paul Kloss (ingest tool)
* private use is permitted
* permission required otherwise

## HTML Documentation

[![Inline docs](http://inch-ci.org/github/dwyl/hapi-auth-jwt2.svg?branch=master)](https://janhoo.github.io/critter/)
