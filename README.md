
<img src="./shiny/www/crabbybanner.png" alt="Critter Logo" width=210/>

#

This page is a stub!

## Overview
Critter is a comprehensive data management solution to essentially replace the previous system of spreadsheets and repositories in ubiquitous use.
The **critter** framework consists of the three modules (i) database, (ii) ingest and curation tool, and (iii) visualization and retrieval tool. Take a look at [this poster](https://zenodo.org/record/1146361/files/critter_poster_arcticchange2017_holstein.pdf) this poster for rationale and background information.

Based on a elaborated, but still simple enough [data model](https://janhoo.github.io/critter/), the   operational data base is the framework's centerpiece which allows concise and coherent data interrogation and building sustainable services for data, visualization, or story telling of top of it.

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

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146361.svg)](https://doi.org/10.5281/zenodo.1146361) Poster

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146542.svg)](https://doi.org/10.5281/zenodo.1146542) Visualization

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146533.svg)](https://doi.org/10.5281/zenodo.1146533) Ingest

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



## Terms of use
This work is owned by Jan Holstein and partly by Paul Kloss (ingest tool)
* private use is permitted
* permission required otherwise

## Contact
* submit suggestions and bug-reports at: https://github.com/janhoo/benthos/issues
* send a pull request on: https://github.com/janhoo/benthos/
* compose a friendly e-mail to:janmholstein[at]gmail(dot)com

## Authors

* Jan Holstein - Data Model, Concept, Architecture & Programming
* Paul Kloss & Jan Holstein - Ingest Tool


## HTML Documentation

https://janhoo.github.io/critter/
