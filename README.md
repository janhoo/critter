# critter
benthic biodiversity datamodel plus toolbox

[![DOI](https://zenodo.org/badge/98420240.svg)](https://zenodo.org/badge/latestdoi/98420240)

This page is a stub!

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

4. use thicc to ingest and curate data. Fire it up with

```
./start.sh
```




## Contributing
1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request :D

## Contact
* submit suggestions and bug-reports at: https://github.com/janhoo/benthos/issues
* send a pull request on: https://github.com/janhoo/benthos/
* compose a friendly e-mail to:janmholstein[at]gmail(dot)com

## Authors

* Jan Holstein & Paul Kloss - Initial work

## License

This code is licensed to you under the terms of the [GNU AFFERO GENERAL PUBLIC LICENSE](http://choosealicense.com/licenses/agpl-3.0/) version 3.0 or higher.

## HTML Documentation

https://janhoo.github.io/critter/
