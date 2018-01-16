
<img src="./shiny/www/crabby_banner.png" alt="Critter Logo" width=210/>

#

This page is a stub!

## Overview
Critter is a comprehensive data management solution to essentially replace the previous system of spreadsheets and repositories in ubiquitous use.
The **critter** framework consists of the three modules (i) database, (ii) ingest and curation tool, and (iii) visualization and retrieval tool. Take a look at [this poster](https://zenodo.org/record/1146361/files/critter_poster_arcticchange2017_holstein.pdf) this poster for rationale and background information [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146361.svg)](https://doi.org/10.5281/zenodo.1146361).
Based on a elaborated, but still simple enough [data model](https://janhoo.github.io/critter/), the   operational data base is the framework's centerpiece which allows concise and coherent data interrogation and building sustainable services for data, visualization, or story telling of top of it.
To help researchers with data ingestion and curation, an ingest tool provides a graphical user interface from where standard operations are performed [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146542.svg)](https://doi.org/10.5281/zenodo.1146542).
The visualization and retrieval tool is a  web-based prototype built to showcase visualization techniques and to enable user-driver demand analysis is currently under evaluation in the ESKP-project [RoaStBiW](https://www.researchgate.net/project/RoaStBiW) with several stakeholders [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1146533.svg)](https://doi.org/10.5281/zenodo.1146533)
https://janhoo.shinyapps.io/arcticcritter/. You can check it out on [janhoo.shinyapps.io](https://janhoo.shinyapps.io/arcticcritter/) or replicate it on you local R environment by 

It consists of three modules.
Centerpiece is the  and the database. The ingest tool helps you



shiny::runGitHub("shiny-examples", "rstudio", subdir = "001-hello")


## Getting started

### Getting started

### Prequisites

* PostgreSQL 9.x
* python3 including pyqt5, xlsxwriter, psycopg2, folium

### Installation



(steps 1+2 only if you want your own database)
1. install postgreSQL 9.x
2. then set up the database
```
cat critterbase/db.ddl.sql | psql -d <YOURDATABASENAME> -U <YOURDBUSER> -h <YOURHOSTe.g.localhost> -p <PORTe.g.5432> -q
```
You can use our database at https://www.awi.de/ourservice .

3. install python3 and the dependencies. If you are lucky, on osx and fine with homebrew,
```
./install_dependencies.sh
```
will do that for you.
Otherwise install
python3 and the packages: pyqt5 xlsxwriter psycopg2 folium

4. use **ingest** to ingest and curate data. Fire it up with

```
./start.sh
```


## Terms of use
This work is owned by Jan Holstein and partly by Paul Kloss (ingest tool)
* private use is permitted
* permission required otherwise

## Contact
* submit suggestions and bug-reports at: https://github.com/janhoo/benthos/issues
* send a pull request on: https://github.com/janhoo/benthos/
* compose a friendly e-mail to:janmholstein[at]gmail(dot)com

## Authors

* Jan Holstein - Data Model & Concept
* Paul Kloss & Jan Holstein - Ingest Tool


## HTML Documentation

https://janhoo.github.io/critter/
