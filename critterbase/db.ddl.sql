CREATE SCHEMA fiona;

CREATE TABLE fiona.crs ( 
	id                   serial  NOT NULL,
	name                 varchar(140) DEFAULT 'WGS84' NOT NULL,
	srid                 integer  ,
	CONSTRAINT pk_crs PRIMARY KEY ( id ),
	CONSTRAINT idx_crs UNIQUE ( name ) 
 );

COMMENT ON TABLE fiona.crs IS 'Link to spatial_ref_sys
The spatial_ref_sys table is a PostGIS included and OGC compliant database table that lists over 3000 known spatial reference systems and details needed to transform/reproject between them.';

COMMENT ON COLUMN fiona.crs.name IS 'Human readable name for the CRS';

COMMENT ON COLUMN fiona.crs.srid IS 'An integer value that uniquely identifies each Spatial Reference System within a database. Same as in Postgis''s spatial_ref_sys';

CREATE TABLE fiona.gear ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	"type"               varchar(140)  ,
	category             varchar(140)  NOT NULL,
	width                float8  ,
	height               float8  ,
	area                 float8  ,
	mass                 float8  ,
	meshsize             float8  ,
	description          varchar(140)  ,
	CONSTRAINT pk_gear PRIMARY KEY ( id ),
	CONSTRAINT idx_gear UNIQUE ( name ) 
 );

ALTER TABLE fiona.gear ADD CONSTRAINT check_gear_typ CHECK ( (category='grab' or category='trawl') );

COMMENT ON CONSTRAINT check_gear_typ ON fiona.gear IS 'ONLA gear of type
''grab'' and ''trawl''
are allowed';

ALTER TABLE fiona.gear ADD CONSTRAINT check_grab_area_exists CHECK ( ((category='grab' and area is not null) or category='trawl') );

COMMENT ON CONSTRAINT check_grab_area_exists ON fiona.gear IS 'wenn category==''grab, dann
muss ''area'' einen Wert haben (nicht NULL)';

COMMENT ON TABLE fiona.gear IS 'Die gear-Tabelle enthält verschiedene Geräte zur Probenahme, sowie deren wichtigste Parameter. Individualisierung der Geräte ist via Attribut "gearname" möglich

REFERENCE BenDa::Xgear
FIXME add constraint that area is madatory if category == "grab"';

COMMENT ON COLUMN fiona.gear.id IS 'Eindeutiger Identifikationsschlüssel für das Gerät

UNIT NONE
REFERENCE BenDa::Xgear::GearID';

COMMENT ON COLUMN fiona.gear.name IS 'Bezeichner des Geraets zB Dredge2.0m
[unique]

REFERENCE BenDa::Sample::GearID';

COMMENT ON COLUMN fiona.gear."type" IS 'Gerätetyp zB VV

REFERENCE BenDa::Xgear::InstrType
FIXME BC, VV, BT, DRE, ...';

COMMENT ON COLUMN fiona.gear.category IS 'Gerätekategorie

REFERENCE NONE
FIXME entweder grab (Greifer) oder trawl (Schleppnetz) oder other';

COMMENT ON COLUMN fiona.gear.width IS 'Breite des Geräts

UNIT m
REFERENCE BenDa::Xgear::Width_m';

COMMENT ON COLUMN fiona.gear.height IS 'Höhe des Geräts

UNIT m
REFERENCE BenDa::Xgear::Height_m';

COMMENT ON COLUMN fiona.gear.area IS 'Fläche des Geräts

UNIT m²
REFERENCE BenDa::Xgear::Area_m2';

COMMENT ON COLUMN fiona.gear.mass IS 'Masse des Geräts

UNIT kg
REFERENCE BenDa::Xgear::Weight_kg';

COMMENT ON COLUMN fiona.gear.meshsize IS 'Maschengröße des Netzes

UNIT mm
REFERENCE BenDa::Xgear::MeshSize_mm
';

COMMENT ON COLUMN fiona.gear.description IS 'Beschreibung als Freitext

REFERENCE BenDa::Xgear::GearDescription';

CREATE TABLE fiona.ingest ( 
	id                   serial  NOT NULL,
	name                 varchar(140) DEFAULT 'anonymous' NOT NULL,
	created_on           timestamp DEFAULT current_timestamp NOT NULL,
	description          varchar(140)  ,
	CONSTRAINT pk_ingest PRIMARY KEY ( id )
 );

CREATE TABLE fiona.lifestage ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	CONSTRAINT lifestageid PRIMARY KEY ( id ),
	CONSTRAINT idx_lifestage UNIQUE ( name ) 
 );

COMMENT ON TABLE fiona.lifestage IS 'Life stage

REFERENCE BenDa::xstages
FIXME indicates if a species is adult (ADU), juvenil (JUV) or larval (LAR). Defaults to ADULT';

COMMENT ON COLUMN fiona.lifestage.id IS 'Unique identifier for lifestage

UNIT NONE
REFERENCE NONE';

COMMENT ON COLUMN fiona.lifestage.name IS 'Life stage

UNIT NONE
REFERENCE BenDa::xstages::STAGE';

CREATE TABLE fiona.person ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	vor_und_nachname     varchar(140)  ,
	affiliation          varchar(140)  ,
	email                varchar(140)  ,
	CONSTRAINT pk_person PRIMARY KEY ( id ),
	CONSTRAINT idx_person UNIQUE ( name ) 
 );

COMMENT ON TABLE fiona.person IS 'Die person-Tabelle beinhaltet Informationen zu allen Personen und Wissenschaftlern, die innerhalb eines Projektes verschiedene Aufnahmen übernehmen können. 

REFERENCE BenDa::Scientist';

COMMENT ON COLUMN fiona.person.id IS 'Eindeutige Identifikationsnummer für die Person

UNIT none
REFERENCE none
';

COMMENT ON COLUMN fiona.person.name IS 'Eindeutiger Bezeichner / Kurzname
[unique]
';

COMMENT ON COLUMN fiona.person.vor_und_nachname IS 'Name im Format [Vorname Nachname]

';

COMMENT ON COLUMN fiona.person.affiliation IS 'Heimatinstitution

REFERENCE BenDa::Scientist::Address';

COMMENT ON COLUMN fiona.person.email IS 'Email-Adresse im Format x@y.z

REFERENCE BenDa::Scientist::Email';

CREATE TABLE fiona.positioningsystem ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	CONSTRAINT pk_positioningsystem PRIMARY KEY ( id ),
	CONSTRAINT idx_positioningsystem UNIQUE ( name ) 
 );

COMMENT ON TABLE fiona.positioningsystem IS 'positioning system used during a particular cruise. (in principle, accuracy can be deduced from this)';

COMMENT ON COLUMN fiona.positioningsystem.id IS 'Unique identifier
 
UNIT NONE
REFERENCE NONE';

COMMENT ON COLUMN fiona.positioningsystem.name IS 'Positionierungssystem des Schiffes 
[unique]
REFERENCE BenDa::Cruise::Positionsystem';

CREATE TABLE fiona."scope" ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  ,
	description          varchar(140)  ,
	CONSTRAINT pk_scope PRIMARY KEY ( id )
 );

COMMENT ON TABLE fiona."scope" IS 'beschreibt eine Gruppe von Taxa die potentiell findbar waren. Dient zur Bestimmung von Absence Daten. 0 := sample wurde nicht auf taxa untersucht

FIXME Constraint/Trigger if exists fk_population_sample_id then sample.scope_id != 0';

CREATE TABLE fiona.scope_taxon ( 
	scope_id             serial  ,
	taxon_id             integer  
 );

CREATE TABLE fiona.ship ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	CONSTRAINT pk_ship PRIMARY KEY ( id ),
	CONSTRAINT idx_ship UNIQUE ( name ) 
 );

COMMENT ON TABLE fiona.ship IS 'used research vessels';

COMMENT ON COLUMN fiona.ship.id IS 'Unique identifier

UNIT none
REFERENCE none';

COMMENT ON COLUMN fiona.ship.name IS 'Reasearch ship name 
[unique]

';

CREATE TABLE fiona.sieve ( 
	id                   serial  NOT NULL,
	"size"               float8  NOT NULL,
	description          varchar(140)  NOT NULL,
	CONSTRAINT sievefracid PRIMARY KEY ( id )
 );

COMMENT ON TABLE fiona.sieve IS 'Sieves used to strip organismes from sediment for  population analysis

REFERENCE BenDa::xsieveFrac';

COMMENT ON COLUMN fiona.sieve.id IS 'Unique identifier of the sieve fraction

UNIT NONE
REFERENCE NONE';

COMMENT ON COLUMN fiona.sieve."size" IS 'Mesh size

UNIT mm
REFERENCE BenDa::xsieveFrac::SieveFraction';

COMMENT ON COLUMN fiona.sieve.description IS 'Beschreibung

REFERENCE BenDa::xsieveFrac::Description';

CREATE TABLE fiona.status ( 
	id                   serial  NOT NULL,
	status               varchar(140)  NOT NULL,
	description          char(140)  ,
	CONSTRAINT pk_status PRIMARY KEY ( id )
 );

COMMENT ON TABLE fiona.status IS 'Status of sample processing, quality control and taxonomix groups sampled.

REFERENCE BenDa::Xstatus
FIXME Overlap w STATION and SAMPLE';

COMMENT ON COLUMN fiona.status.status IS 'Unique identifier for status.

UNIT NONE
REFERENCE BenDa::Xstatus:Status';

COMMENT ON COLUMN fiona.status.description IS 'Beschreibung

REFERENCE BenDa::Xstatus::Description';

CREATE TABLE fiona.table_struct ( 
	tablename            varchar(140)  NOT NULL,
	is_lookup            bool  ,
	lpk                  char(140)  ,
	daddy                char(140)  ,
	CONSTRAINT pk_table_struct PRIMARY KEY ( tablename )
 );

COMMENT ON COLUMN fiona.table_struct.lpk IS '(Human readable) Local Primary Key';

COMMENT ON COLUMN fiona.table_struct.daddy IS 'Vatertabelle';

CREATE TABLE fiona.taxon ( 
	id                   serial  NOT NULL,
	aaid                 integer  ,
	is_colony            bool  ,
	aid                  integer  NOT NULL,
	url                  varchar(140)  ,
	scientificname       varchar(140)  ,
	authority            varchar(140)  ,
	status               varchar(140)  ,
	unacceptreason       varchar(140)  ,
	rank                 varchar(140)  ,
	vaid                 integer  ,
	valid_name           varchar(140)  ,
	valid_authority      varchar(140)  ,
	kingdom              varchar(140)  ,
	phylum               varchar(140)  ,
	klasse               varchar(140)  ,
	ordnung              varchar(140)  ,
	family               varchar(140)  ,
	genus                varchar(140)  ,
	citation             varchar(990)  ,
	lsid                 varchar(140)  ,
	ismarine             integer  ,
	isbrackish           integer  ,
	isfreshwater         integer  ,
	isterrestrial        integer  ,
	isextinct            integer  ,
	match_type           varchar(140)  ,
	modified             varchar(140)  ,
	CONSTRAINT pk_worms PRIMARY KEY ( id ),
	CONSTRAINT idx_taxon UNIQUE ( aid ) 
 );

COMMENT ON TABLE fiona.taxon IS 'Comprehensive table of all taxa that can possibly be in the BD.
Contains information form www.marinespecies.org (WORMS),
plus is_colony and aaid (the aid of the accepted species) which is used to
map the taxon_id of population.taxon to the id of the currently accepted (WORMS) taxon. 


UNIT none
REFERENCE www.marinspecies.org, github.com/janhoo/worms';

COMMENT ON COLUMN fiona.taxon.aaid IS 'accepted aphia ID

an entry in taxon.aid with this particular aaid must exist!!
(FK not possible bc of NA)';

COMMENT ON COLUMN fiona.taxon.aid IS 'AphiaID

REFERENCE: AphiaID Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.url IS 'url 
REFERENCE: url Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.scientificname IS 'scientificname

REFERENCE: scientificname Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.authority IS 'authority
REFERENCE: authority Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.status IS 'status


REFERENCE: status Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.unacceptreason IS 'unacceptreason
REFERENCE: unacceptreason Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.rank IS 'rank

REFERENCE: rank Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.vaid IS 'valid_aphiaid

REFERENCE: valid_aphiaid Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.valid_name IS 'valid_name
REFERENCE: valid_name Field from WORMS (marinspecies.org)
';

COMMENT ON COLUMN fiona.taxon.valid_authority IS 'valid_authority
REFERENCE: valid_authority Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.kingdom IS 'kingdom
REFERENCE: kingdom Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.phylum IS 'phylum
REFERENCE: phylum Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.klasse IS 'Klasse
REFERENCE: class Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.ordnung IS 'ordnung
REFERENCE: order Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.family IS 'family
REFERENCE: family Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.genus IS 'genus
REFERENCE: genus Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.citation IS 'citation
REFERENCE: citation Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.lsid IS 'lsid
REFERENCE: lsid Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.ismarine IS 'ismarine
REFERENCE: ismarine Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.isbrackish IS 'isbrackish
REFERENCE: isbrackish Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.isfreshwater IS 'isfreshwater
REFERENCE: isfreshwater Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.isterrestrial IS 'isterrestrial
REFERENCE: isterrestrial Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.isextinct IS 'isextinct
REFERENCE: isextinct Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.match_type IS 'match_type
REFERENCE: match_type Field from WORMS (marinspecies.org)';

COMMENT ON COLUMN fiona.taxon.modified IS 'modification date
REFERENCE: modified Field from WORMS (marinspecies.org)';

CREATE TABLE fiona.cruise ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	ingest_id            integer  NOT NULL,
	crs_id               integer  NOT NULL,
	ship_id              integer  ,
	positioningsystem_id integer  ,
	lead_person_id       integer  ,
	start_on             date  ,
	end_on               date  ,
	region               varchar(140)  ,
	project              varchar(140)  ,
	institute            varchar(140)  ,
	client               varchar(140)  ,
	remark               varchar(140)  ,
	CONSTRAINT pk_cruise PRIMARY KEY ( id ),
	CONSTRAINT idx_cruise UNIQUE ( name ) 
 );

CREATE INDEX idx_cruise_0 ON fiona.cruise ( positioningsystem_id );

CREATE INDEX idx_cruise_2 ON fiona.cruise ( ship_id );

CREATE INDEX idx_cruise_3 ON fiona.cruise ( lead_person_id );

CREATE INDEX idx_cruise_1 ON fiona.cruise ( crs_id );

CREATE INDEX idx_cruise_4 ON fiona.cruise ( ingest_id );

COMMENT ON TABLE fiona.cruise IS 'Die cruise-Tabelle enthält alle relevanten Informationen, welche für die gesamte Ausfahrt von Bedeutung sind.

REFERENCE BenDa::Cruise';

COMMENT ON COLUMN fiona.cruise.id IS 'Unique identifier for each cruise/expedition within the database.

UNIT NONE
REFERENCE BenDa::Cruise::CruiseID';

COMMENT ON COLUMN fiona.cruise.name IS 'Assigned cruise code
[unique]

REFERENCE BenDa::Cruise::CruiseCode';

COMMENT ON COLUMN fiona.cruise.crs_id IS 'crs.id (FK) of the used coordinate reference';

COMMENT ON COLUMN fiona.cruise.ship_id IS 'ship.id (FK) of the used research ship

UNIT none
REFERENCE none';

COMMENT ON COLUMN fiona.cruise.positioningsystem_id IS 'Used positionsystem::positionsystemid of the ship

UNIT none
REFERENCE BenDa::Cruise:Positionsystem';

COMMENT ON COLUMN fiona.cruise.lead_person_id IS 'person::personid [FK] of the scientific cruise leader

UNIT none
REFERENCE BenDa::Cruise::SciCruiseleader';

COMMENT ON COLUMN fiona.cruise.start_on IS 'Start date of the cruise

FORMAT ''YYYY-MM-DD''.
REFERENCE BenDa::Cruise::STARTDATE';

COMMENT ON COLUMN fiona.cruise.end_on IS 'End date of the cruise

FORMAT ''YYYY-MM-DD''.
REFERENCE BenDa::Cruise::ENDDATE';

COMMENT ON COLUMN fiona.cruise.region IS 'Description of sea area, not further defined: could be e.g. North Sea, German Bight or Doggerbank

REFERENCE BenDa::Cruise::SeaArea';

COMMENT ON COLUMN fiona.cruise.project IS 'Name of the Project.

REFERENCE BenDa::Cruise::Project';

COMMENT ON COLUMN fiona.cruise.institute IS 'Name of project''s affiliated institution.

REFERENCE BenDa::Cruise::Institute';

COMMENT ON COLUMN fiona.cruise.client IS 'Auftraggeber

REFERENCE BenDa::Cruise::Client';

COMMENT ON COLUMN fiona.cruise.remark IS 'Kommentar.

REFERENCE BenDa::Cruise::Remark';

CREATE TABLE fiona.dataset ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	lineage              varchar(140)  ,
	reference_person     varchar(140)  ,
	realm                varchar(140)  ,
	doi                  varchar(140)  ,
	contact_person_id    integer  ,
	description          varchar(140)  ,
	free_access          bool DEFAULT true NOT NULL,
	CONSTRAINT pk_dataset_0 PRIMARY KEY ( id ),
	CONSTRAINT idx_dataset_0 UNIQUE ( name ) 
 );

CREATE INDEX idx_dataset_1 ON fiona.dataset ( contact_person_id );

COMMENT ON TABLE fiona.dataset IS 'Metadaten zu datensaetzen, qualitaetsmanagement, provienenz, etc';

COMMENT ON COLUMN fiona.dataset.id IS 'Primaerschluessel';

COMMENT ON COLUMN fiona.dataset.name IS 'Eindeutiger Bezeichner des Datensatzes';

COMMENT ON COLUMN fiona.dataset.lineage IS 'Provenienz';

COMMENT ON COLUMN fiona.dataset.reference_person IS 'Ansprechpartner';

COMMENT ON COLUMN fiona.dataset.realm IS 'Geografischer Bereich';

COMMENT ON COLUMN fiona.dataset.doi IS 'Digital Object Identifier';

COMMENT ON COLUMN fiona.dataset.contact_person_id IS '(Inhouse) Kontakt für diesen Datensatz';

COMMENT ON COLUMN fiona.dataset.description IS 'Beschreibung';

COMMENT ON COLUMN fiona.dataset.free_access IS 'Frei Zur Verwendung

FIXME: Definition Verwendung, Inhouse/extern, QM';

CREATE TABLE fiona.station ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	cruise_id            integer  NOT NULL,
	ingest_id            integer  NOT NULL,
	responsible_person_id integer  ,
	status_id            integer  ,
	start_lon            numeric(11,8)  ,
	start_lat            numeric(11,8)  ,
	start_on             date  ,
	start_time           time  ,
	start_depth          float8  ,
	end_lon              numeric(11,8)  ,
	end_lat              numeric(11,8)  ,
	end_on               date  ,
	end_time             time  ,
	end_depth            float8  ,
	"location"           varchar(140)  ,
	target_lon           numeric(11,8)  ,
	target_lat           numeric(11,8)  ,
	replicates           integer  ,
	temperature_air      float8  ,
	temperature_surfacewater float8  ,
	temperature_bottomwater float8  ,
	salinity_surfacewater float8  ,
	salinity_bottomwater float8  ,
	oxygen_bottomwater   float8  ,
	windspeed_beaufort   float8  ,
	wind_direction       varchar(140)  ,
	remark               varchar(500)  ,
	CONSTRAINT pk_station PRIMARY KEY ( id )
 );

CREATE INDEX idx_station_1 ON fiona.station ( status_id );

CREATE INDEX idx_station_2 ON fiona.station ( responsible_person_id );

CREATE INDEX idx_station ON fiona.station ( cruise_id );

CREATE INDEX idx_station_0 ON fiona.station ( ingest_id );

COMMENT ON TABLE fiona.station IS 'In der station-Tabelle werden allgemeine Informationen für die entsprechenden Stationen gesammelt. Stationen werden während einer CRUISE angefahren und verschiedene GEARS eingesetzt um SAMPLES zu gewinnen 

REFERENCE BenDa::Station';

COMMENT ON COLUMN fiona.station.id IS '[PK] Unique station identifier

UNIT NONE
REFERENCE BenDa::Station::StationID';

COMMENT ON COLUMN fiona.station.name IS 'Stationsname

REFERENCE BenDa::Station::Station
[Local PK]';

COMMENT ON COLUMN fiona.station.cruise_id IS '[PFK] Associated cruise.cruiseid

UNIT NONE
REFERENCE BenDa::Station::CruiseID';

COMMENT ON COLUMN fiona.station.responsible_person_id IS 'person
[FK]

REFERENCE BenDa::Station::ProectLeader
FIXME sinnvoll wäre hier Protokollführer oder Verantwortlicher vom Dienst';

COMMENT ON COLUMN fiona.station.status_id IS 'Status der Daten

REFERENCE BenDa::Station::DataStatus';

COMMENT ON COLUMN fiona.station.start_lon IS 'Logged longitude upon arrival at the station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::StartLon';

COMMENT ON COLUMN fiona.station.start_lat IS 'Logged latitude upon arrival at the station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::StartLat';

COMMENT ON COLUMN fiona.station.start_on IS 'Dateof arrival at the station

FORMAT ''YYYY-MM-DD''
REFERENCE BenDa::Station::StartDate
';

COMMENT ON COLUMN fiona.station.start_time IS 'Time of arrival at the station

FORMAT ''HH:MM:SS''
REFERENCE BenDa::Station::StartDate';

COMMENT ON COLUMN fiona.station.start_depth IS 'Depth at station arrival.

UNIT m unter Bezugsfläche (>0)
REFERENCE BenDa::Station::StartDepth

TO DO - BenDa issue ticket 9';

COMMENT ON COLUMN fiona.station.end_lon IS 'Logged longitude at depature of the station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::EndLon';

COMMENT ON COLUMN fiona.station.end_lat IS 'Logged latitude at depature of the station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::EndLat';

COMMENT ON COLUMN fiona.station.end_on IS 'Date of departure from station

FORMAT ''YYYY-MM-DD''
REFERENCE BenDa::Station::EndDate
';

COMMENT ON COLUMN fiona.station.end_time IS 'Time of departure from the station

FORMAT ''HH:MM:SS''
REFERENCE BenDa::Station::StartDate';

COMMENT ON COLUMN fiona.station.end_depth IS 'Water depth at depature from station.

UNIT m unter Bezugsfläche (>0)
REFERENCE BenDa::Station::DepthEnd
TO DO - Benda issue ticket 9';

COMMENT ON COLUMN fiona.station."location" IS 'Name der Station, wenn diese ausserhable der ''cruise'' existiert (zB Dauerstationen / alternative Namenschemata).

REFERENCE BenDa::Station::Area';

COMMENT ON COLUMN fiona.station.target_lon IS 'Longitude of targeted station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::LonTarget';

COMMENT ON COLUMN fiona.station.target_lat IS 'Latitude of targeted station

UNIT/FORMAT decimal degrees
REFERENCE BenDa::Station::LatTarget';

COMMENT ON COLUMN fiona.station.replicates IS 'Anzahl der Replikate (Geräte pro Station)


UNIT NONE
REFERENCE BenDa::Station::No_Replicates';

COMMENT ON COLUMN fiona.station.temperature_air IS 'Air temperature in Celsius

UNIT Grad Celsius
REFERENCE BenDa::Station::TempAir';

COMMENT ON COLUMN fiona.station.temperature_surfacewater IS 'Sea surface temperature (SST)

UNIT Grad Celsius
REFERENCE BenDa::Station::TempSurf';

COMMENT ON COLUMN fiona.station.temperature_bottomwater IS 'Sea bottom temperature (SBT)

UNIT Grad Celsius
REFERENCE BenDa::Station::TempBot';

COMMENT ON COLUMN fiona.station.salinity_surfacewater IS 'Salinity at sea surface.

UNIT PSU
REFERENCE BenDa::Station::SalinitySurf';

COMMENT ON COLUMN fiona.station.salinity_bottomwater IS 'Salinity at sea bottom.

UNIT PSU
REFERENCE BenDa::Station::SalinityBot';

COMMENT ON COLUMN fiona.station.oxygen_bottomwater IS 'Oxidation level of bottom water

UNIT mg/l
REFERENCE BenDa::Station::WaterOxyBot';

COMMENT ON COLUMN fiona.station.windspeed_beaufort IS 'Beaufort number for observed conditions at sea, assigned after the Beaufort wind force scale. Dezimals are allowed 

UNIT Bft
REFERENCE BenDa::Station::Windspeed';

COMMENT ON COLUMN fiona.station.wind_direction IS 'Wind direction in text format, e.g. NW for north-west

UNIT NONE
REFERENCE BenDa::Station::Winddirection
FIXME allowed categories e.g. NW NNW WNW ';

COMMENT ON COLUMN fiona.station.remark IS 'Remark

REFERENCE BenDa::Station::Remark';

CREATE TABLE fiona.sample ( 
	id                   serial  NOT NULL,
	name                 varchar(140)  NOT NULL,
	station_id           integer  NOT NULL,
	gear_id              integer  NOT NULL,
	dataset_id           integer  NOT NULL,
	ingest_id            integer  NOT NULL,
	status_id            integer  ,
	responsible_person_id integer  ,
	scope_id             integer DEFAULT 0 NOT NULL,
	area                 float8  ,
	start_lon            numeric(11,8)  NOT NULL,
	start_lat            numeric(11,8)  NOT NULL,
	start_on             date  NOT NULL,
	start_time           time  ,
	start_on_error       integer DEFAULT 0 ,
	start_depth          float8  ,
	end_lon              numeric(11,8)  ,
	end_lat              numeric(11,8)  ,
	end_on               date  ,
	end_time             time  ,
	end_depth            float8  ,
	replicate_number     integer  ,
	sample_mass          real DEFAULT 0 ,
	subsample_mass       real  ,
	subsample_share      real  ,
	sampling_distance    float8  ,
	method_biomass       varchar(140)  ,
	method_biomass_dry   varchar(140)  ,
	method_biomass_afdm  varchar(140)  ,
	method_conservation  varchar(140)  ,
	temperature_surfacewater_start float8  ,
	temperature_surfacewater_end float8  ,
	salinity_surfacewater_start float8  ,
	salinity_surfacewater_end float8  ,
	remark               varchar(500)  ,
	CONSTRAINT pk_sample PRIMARY KEY ( id )
 );

CREATE INDEX idx_sample ON fiona.sample ( station_id );

CREATE INDEX idx_sample_1 ON fiona.sample ( responsible_person_id );

CREATE INDEX idx_sample_2 ON fiona.sample ( gear_id );

CREATE INDEX idx_sample_3 ON fiona.sample ( status_id );

CREATE INDEX idx_sample_0 ON fiona.sample ( ingest_id );

CREATE INDEX idx_sample_4 ON fiona.sample ( dataset_id );

CREATE INDEX idx_sample_5 ON fiona.sample ( scope_id );

COMMENT ON TABLE fiona.sample IS 'Die sample-Tabelle enthaelt Informationen ueber die Proben aus einem einzelnen Geraeteeinsatz. 

REFERENCE BenDa::Sample';

COMMENT ON COLUMN fiona.sample.id IS 'Primaerschluessel der Station

UNIT NONE
REFERENCE BenDa::Sample::SampleID';

COMMENT ON COLUMN fiona.sample.name IS 'laufender bezeichner für samples dieser station
[Local PK]';

COMMENT ON COLUMN fiona.sample.station_id IS '[PFK] stationID der der Probe uebergeordneten zugehoerigen Station

UNIT NONE
REFERENCE BenDa::Sample::StationID';

COMMENT ON COLUMN fiona.sample.gear_id IS '[FK] gearID des Geraetes, welches zur Probennahme genutzt wurde. 

UNIT NONE
REFERENCE BenDa::Sample::Gear';

COMMENT ON COLUMN fiona.sample.status_id IS 'Status of sample processing, quality control and taxonomix groups sampled, as classified in the status table

REFERENCE BenDa::Sample::Status';

COMMENT ON COLUMN fiona.sample.responsible_person_id IS 'personID des verantwortlichen Wissenschaftlers für die Probenahme

UNIT NONE
REFERENCE BenDa::Sample::RespScientist';

COMMENT ON COLUMN fiona.sample.scope_id IS 'identifies taxa that was looked for
0 := no biological analysis was carried out

REFERENCE none
';

COMMENT ON COLUMN fiona.sample.area IS 'Beprobte Flaeche

relevant für ''trawls''. Bei ''grabs'' siehe gear.area
UNIT sqm
REFERENCE BenDa::Bcatch::SampledArea
NOTE  if !NULL overrides gear.area 
NOTE if NULL & gear.cat==trawl: means area unknown == presence only information';

COMMENT ON COLUMN fiona.sample.start_lon IS 'Laengengrad bei Beginn der Probenahme

UNIT/FORMAT  decimal degrees
REFERENCE BenDa::Sample::SampleStartLon';

COMMENT ON COLUMN fiona.sample.start_lat IS 'Breitengrad bei Beginn der Probenahme

UNIT/FORMAT  decimal degrees
REFERENCE BenDa::Sample::SampleStartLat';

COMMENT ON COLUMN fiona.sample.start_on IS 'Startdatum der Probenahme

FORMAT ''YYYY-MM-DD''
REFERENCE BenDa::Sample::SampleStartDate';

COMMENT ON COLUMN fiona.sample.start_time IS 'Zeit Anfang Probenahme

FORMAT ''HH:MM:SS''';

COMMENT ON COLUMN fiona.sample.start_on_error IS 'Ungenauigkeitin der Datumsangabe in Tagen
bspw. nur jahr bekannt
  start_date<-2017-06-31
  start_date_error<-132
bspw. nur JJ.MM bekannt
  start_date<-2017-04-15
  start_date_error<-15';

COMMENT ON COLUMN fiona.sample.start_depth IS 'Wassertiefe bei Beginn der Probenahme

UNIT m unter Bezugsfläche (>0)
REFERENCE BenDa::Sample::SampleStartDepth';

COMMENT ON COLUMN fiona.sample.end_lon IS 'Laengengrad bei Ende der Probenahme

UNIT/FORMAT  decimal degrees
REFERENCE BenDa::Sample::SampleEndLon';

COMMENT ON COLUMN fiona.sample.end_lat IS 'Breitengrad bei Ende der Probenahme

UNIT/FORMAT  decimal degrees
REFERENCE BenDa::Sample::SampleEndLat';

COMMENT ON COLUMN fiona.sample.end_on IS 'Enddatum der Probenahme 

FORMAT YYYY-MM-DD
REFERENCE BenDa::Sample::SampleEndDate';

COMMENT ON COLUMN fiona.sample.end_time IS 'Zeit ende Probenahme

FORMAT ''HH:MM:SS''';

COMMENT ON COLUMN fiona.sample.end_depth IS 'Wassertiefe bei Ende der Probenahme

UNIT m unter Bezugsfläche (>0)
REFERENCE BenDa::Sample::SampleEndDepth';

COMMENT ON COLUMN fiona.sample.replicate_number IS 'Nummer des Replikats der Probe

UNIT NONE
REFERENCE BenDa::Sample::Replicate';

COMMENT ON COLUMN fiona.sample.sample_mass IS 'Total mass of haul/sample, only relevant for trawled gears (net towed).

UNIT kg
REFERENCE BenDa::Sample::SampleSize';

COMMENT ON COLUMN fiona.sample.subsample_mass IS 'Total mass of sub-haul/sub-sample of total catch, only relevant for trawled gears (net towed).

UNIT kg
REFERENCE BenDa::Sample::SubSampleSize';

COMMENT ON COLUMN fiona.sample.subsample_share IS 'Factor for extrapolating subsample to total catch size 
( = sample weight/subsample weight)

UNIT kg/kg
REFERENCE BenDa::Sample::TotalSubFactor
';

COMMENT ON COLUMN fiona.sample.sampling_distance IS 'Total trawling distance of sample, only relevant for trawled/towed gears (net towed).

UNIT m
WARNING You may not use this to calculate catch. For this, use sample.sampled_area
REFERENCE BenDa::Sample::SamplingDistance';

COMMENT ON COLUMN fiona.sample.method_biomass IS 'Weight determined with or without shell (molluscs)

REFERENCE BenDa::Sample::BiomassDeterm

FIXME  1 = after shell removement, 2 = with shell
FIXME thisis valid for all method_biomass_xxx, is it?';

COMMENT ON COLUMN fiona.sample.method_biomass_dry IS 'Method to obtain Drymass

REFERENCE BenDa::Sample::DrywDeterm
FIXME  1 = measured, 2 = calculated by species conversion factor
';

COMMENT ON COLUMN fiona.sample.method_biomass_afdm IS 'Method to obtain ash free drymass

REFERENCE BenDa::Sample::AFDWDeterm
FIXME  1 = measured, 2 = calculated by species conversion factor
';

COMMENT ON COLUMN fiona.sample.method_conservation IS 'Conservation method for sample

REFERENCE BenDa::Sample::Conservation
FIXME Alk = 70%Alkohol, For = Formaldehyde, Frz = Frozen
';

COMMENT ON COLUMN fiona.sample.temperature_surfacewater_start IS 'Wassertemperatur an der Oberfläche bei Beginn der Probenahme

UNIT Grad Celsius
REFERENCE BenDa::Sample::SampleStartTemp_surf';

COMMENT ON COLUMN fiona.sample.temperature_surfacewater_end IS 'Wassertemperatur an der Oberfläche bei Ende der Probenahme

UNIT Grad Celsius
REFERENCE BenDa::Sample::SampleEndTemp_surf';

COMMENT ON COLUMN fiona.sample.salinity_surfacewater_start IS 'Salinitaet des Oberflaechenwassers bei Beginn der Probenahme 

UNIT PSU
REFERENCE BenDa::Sample::SampleStartSal_surf';

COMMENT ON COLUMN fiona.sample.salinity_surfacewater_end IS 'Salinität des Oberflächenwassers bei Ende der Probenahme

UNIT PSU
REFERENCE BenDa::Sample::SampleEndSal_surf';

COMMENT ON COLUMN fiona.sample.remark IS 'Kommentar

REFERENCE BenDa::Sample::Remark';

CREATE TABLE fiona.sediment ( 
	id                   serial  NOT NULL,
	sample_id            integer  NOT NULL,
	ingest_id            integer  NOT NULL,
	median               float8  ,
	gsd                  float8  ,
	weight               float8  ,
	grab_pd              float8  ,
	method_grainsize     varchar(140)  ,
	temperature          float8  ,
	c_org                float8  ,
	c_total              float8  ,
	loss_on_ignition     float8  ,
	nitrogen             float8  ,
	sulfur               float8  ,
	oxygen_pd            float8  ,
	smell                varchar(140)  ,
	description          varchar(140)  ,
	remark               varchar(140)  ,
	fuz_silt             integer  ,
	fuz_vfsand           integer  ,
	fuz_fsand            integer  ,
	fuz_msand            integer  ,
	fuz_csand            integer  ,
	fuz_vcsand           integer  ,
	fuz_gravel           integer  ,
	fuz_stones           integer  ,
	fuz_shell            integer  ,
	fuz_clay             integer  ,
	CONSTRAINT pk_sediment PRIMARY KEY ( id ),
	CONSTRAINT idx_sediment UNIQUE ( sample_id ) 
 );

CREATE INDEX idx_sediment_0 ON fiona.sediment ( ingest_id );

COMMENT ON TABLE fiona.sediment IS 'Visuelle Sedimentansprache

UNIT NONE
REFERENCE BenDa::Sediment';

COMMENT ON COLUMN fiona.sediment.id IS '[PK] Unique identifier for sediment

UNIT none
REFERENCE none';

COMMENT ON COLUMN fiona.sediment.sample_id IS 'Primaerschluessel der Station

UNIT NONE
REFERENCE BenDa::Sample::SampleID';

COMMENT ON COLUMN fiona.sediment.median IS 'Median grain size  

UNIT Mikrometer
BenDa::Sediment::Median
FIXME calculated by percental parts of different grainsizes';

COMMENT ON COLUMN fiona.sediment.gsd IS 'Sorting coefficient sigma1 of sediment 

UNIT none
BenDa::Sediment::GSD
FIXME  calculated by percental parts of different grainsizes ';

COMMENT ON COLUMN fiona.sediment.weight IS 'Total weight of sediment sample used for grainsize determination

UNIT g und Kilo (manchmal 0)
REFERENCE BenDa::Sediment::SAMPLEWEIGHT
FIXME Einheit wahrscheinlich auch z. T.  Kilogramm (manchmal 0)';

COMMENT ON COLUMN fiona.sediment.grab_pd IS 'Penetration depth of the grab into the sediment

UNIT cm
BenDa::Sediment::PenetrationDepth';

COMMENT ON COLUMN fiona.sediment.method_grainsize IS 'Method used to determine grainsizes 


REFERENCE BenDa::Sediment::GRAINSIZEMETHOD
FIXME (e.g. DIN- 18 122, Trockensiebung etc.)';

COMMENT ON COLUMN fiona.sediment.temperature IS 'Measured ex situ sediment temperature

UNIT Grad Celsius
BenDa::Sediment::SedTemp';

COMMENT ON COLUMN fiona.sediment.c_org IS 'Organic carbon content of the sediment 

UNIT g/kg
BenDa::Sediment::CORG';

COMMENT ON COLUMN fiona.sediment.c_total IS 'total carbon content in sediment sample 

UNIT %
BenDa::Sediment::CTotal';

COMMENT ON COLUMN fiona.sediment.loss_on_ignition IS 'Loss on ignition as a measure of sediment organic matter 

UNIT %
BenDa::Sediment::LOSSONIGITION';

COMMENT ON COLUMN fiona.sediment.nitrogen IS 'total nitrogen content in sediment sample 

UNIT %
BenDa::Sediment::Nitrogen';

COMMENT ON COLUMN fiona.sediment.sulfur IS 'total sulfur content in sediment sample 

UNIT %
BenDa::Sediment::Sulfur';

COMMENT ON COLUMN fiona.sediment.oxygen_pd IS 'Oxygen Penetration Depth as per ex situ visual inspection

UNIT mm
BenDa::Sediment::OxyLayer
FIXME method';

COMMENT ON COLUMN fiona.sediment.smell IS 'General description of sediment smell (e.g. smell of sulfur)


REFERENCE BenDa::Sediment::SedSmell';

COMMENT ON COLUMN fiona.sediment.description IS 'General sediment description of texture, appearance and any other characteristics (e.g. silty fine sand, strong bioturbation marks etc.



REFERENCE BenDa::Sediment::SedDescription';

COMMENT ON COLUMN fiona.sediment.remark IS 'Remarks for  sediment description of texture, appearance and any other characteristics (e.g.  strong bioturbation marks etc.

REFERENCE BenDa::Sediment::Remark
FIXME overlap w sed_description';

COMMENT ON COLUMN fiona.sediment.fuz_silt IS 'Fuzzy coding of silt fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::Silt';

COMMENT ON COLUMN fiona.sediment.fuz_vfsand IS 'Fuzzy coding of very fine sand fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::VFSand';

COMMENT ON COLUMN fiona.sediment.fuz_fsand IS 'Fuzzy coding of fine sand fraction of sediment sample by numbers between 1-3
BenDa::Sediment::FSand';

COMMENT ON COLUMN fiona.sediment.fuz_msand IS 'Fuzzy coding of medium sand fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::MSand';

COMMENT ON COLUMN fiona.sediment.fuz_csand IS 'Fuzzy coding of coarse sand fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::CSand';

COMMENT ON COLUMN fiona.sediment.fuz_vcsand IS 'Fuzzy coding of very coarse sand fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::VCSand';

COMMENT ON COLUMN fiona.sediment.fuz_gravel IS 'Fuzzy coding of gravel fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::Gravel';

COMMENT ON COLUMN fiona.sediment.fuz_stones IS 'Fuzzy coding of stones fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::Stones';

COMMENT ON COLUMN fiona.sediment.fuz_shell IS 'Fuzzy coding of shell (from e.g. Molluscs) fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::Shell';

COMMENT ON COLUMN fiona.sediment.fuz_clay IS 'Fuzzy coding of clay fraction of sediment sample by numbers between 1-3

UNIT NONE
REFERENCE BenDa::Sediment::Clay';

CREATE TABLE fiona.sieveanalysis ( 
	id                   serial  NOT NULL,
	sample_id            integer  NOT NULL,
	ingest_id            integer  NOT NULL,
	residue              float8  NOT NULL,
	meshsize             float8  NOT NULL,
	CONSTRAINT pk_sieveanalysis PRIMARY KEY ( id )
 );

CREATE INDEX idx_sieveanalysis ON fiona.sieveanalysis ( sample_id );

CREATE INDEX idx_sieveanalysis_0 ON fiona.sieveanalysis ( ingest_id );

COMMENT ON TABLE fiona.sieveanalysis IS 'Korngrössen- bzw. Siebanalysen 

UNIT NONE
REFERENCE NONE';

COMMENT ON COLUMN fiona.sieveanalysis.id IS '[PK] Unique identifier for sieveanalysis

UNIT NONE
REFERENCE NONE';

COMMENT ON COLUMN fiona.sieveanalysis.sample_id IS '[PK] Unique identifier for sediment

UNIT none
REFERENCE none';

COMMENT ON COLUMN fiona.sieveanalysis.residue IS 'Einwage pro Sieb
UNIT Procent
REFERENCE BenDa::Sediment::GRAINSIZE1 - .GRAINSIZE8';

COMMENT ON COLUMN fiona.sieveanalysis.meshsize IS 'Maschenweite des Siebes 

UNIT Mikrometer
REFERENCE NONE';

CREATE TABLE fiona.population ( 
	id                   serial  NOT NULL,
	sample_id            integer  NOT NULL,
	taxon_id             integer  NOT NULL,
	sieve_id             integer  ,
	lifestage_id         integer  ,
	ingest_id            integer  NOT NULL,
	"number"             numeric  ,
	biomass_wet          float8  ,
	biomass_dry          float8  ,
	biomass_afdm         float8  ,
	subsample_share      varchar(500)  ,
	remark               varchar(500)  ,
	given_aphiaid        integer  NOT NULL,
	given_taxon_name     varchar(140)  NOT NULL,
	given_gear_name      varchar(140)  NOT NULL,
	given_lon            numeric  NOT NULL,
	given_lat            numeric  NOT NULL,
	given_date           date  NOT NULL,
	CONSTRAINT populationid PRIMARY KEY ( id )
 );

CREATE INDEX idx_population_0 ON fiona.population ( sample_id );

CREATE INDEX idx_population_1 ON fiona.population ( sieve_id );

CREATE INDEX idx_population_2 ON fiona.population ( lifestage_id );

CREATE INDEX idx_population_3 ON fiona.population ( ingest_id );

CREATE INDEX idx_population ON fiona.population ( taxon_id );

COMMENT ON TABLE fiona.population IS 'Alle Taxa incl. Abundanz(number) und biomasse (sum_xxx) pro sample

REFERENCE BenDa::Bcatch';

COMMENT ON COLUMN fiona.population.id IS '[PK] Eindeutige Identifikationsnummer des Eintrags

UNIT NONE
REFERENCE BenDa::Bcatch::BcatchID';

COMMENT ON COLUMN fiona.population.sample_id IS '[PFK] ID der Probenahme

UNIT NONE
REFERENCE BenDa::Bcatch::SampleID';

COMMENT ON COLUMN fiona.population.taxon_id IS 'taxonid (FK) for the record to use.

UNIT none
REFERENCE none';

COMMENT ON COLUMN fiona.population.sieve_id IS 'Siebfraktion

UNIT NONE
REFERENCE BenDa::Bcatch::SieveFraction';

COMMENT ON COLUMN fiona.population.lifestage_id IS 'life_stage::stageid: Developmental stage of species, i.e. indicate if larval or juvenil, see table life_stage

UNIT NONE
REFERENCE BenDa::Bcatch::Stage';

COMMENT ON COLUMN fiona.population."number" IS 'Anzahl der Individuen pro sample.sampled_area
(Beachten: Abhängig von gear.gearcategory, sample.sampled_area ist unterschiedlich definiert. )

UNIT NONE
REFERENCE BenDa::Bcatch::Number

FIXME:Bezugsgroesse Quadratmeter?''';

COMMENT ON COLUMN fiona.population.biomass_wet IS 'Total wetmass per taxon in sample pro sample.sampled_area
(Beachten: Abhängig von gear.gearcategory, sample.sampled_area ist unterschiedlich definiert. )

UNIT g
REFERENCE BenDa::Bcatch::Wetsum';

COMMENT ON COLUMN fiona.population.biomass_dry IS 'Total drymass per taxon in sample in gramm pro sample.sampled_area
(Beachten: Abhängig von gear.gearcategory, sample.sampled_area ist unterschiedlich definiert. )

UNIT g
REFERENCE BenDa::Bcatch::Drysum';

COMMENT ON COLUMN fiona.population.biomass_afdm IS 'Total ash free dry mass per taxon in sample in gramm pro sample.sampled_area
(Beachten: Abhängig von gear.gearcategory, sample.sampled_area ist unterschiedlich definiert. )

UNIT g
REFERENCE BenDa::Bcatch::AFDWsum';

COMMENT ON COLUMN fiona.population.subsample_share IS 'subsample weight share

A subsample was taken bc of high sample amount
subsample_share = subsample weight/sample weight

ALL NUMBERS IN POPULATION RELATE TO THE TOTAL SAMPLE
(and are extrapolates in case of subsampling)


REFERENCE BenDa::Bcatch::Remark_SubTotalFactor
FIXME terrible naming, revert to fraction (10 -> 0.1)';

COMMENT ON COLUMN fiona.population.remark IS 'Kommentar


REFERENCE BenDa::Bcatch::Remark';

COMMENT ON COLUMN fiona.population.given_aphiaid IS 'original aphia id as in ingest

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

COMMENT ON COLUMN fiona.population.given_taxon_name IS 'original taxonname id as in ingest

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

COMMENT ON COLUMN fiona.population.given_gear_name IS 'original gearname id as in ingest

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

COMMENT ON COLUMN fiona.population.given_lon IS 'original longitude as in ingest

UNIT/FORMAT  decimal degrees WGS84

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

COMMENT ON COLUMN fiona.population.given_lat IS 'original latitude as in ingest

UNIT/FORMAT  decimal degrees WGS84

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

COMMENT ON COLUMN fiona.population.given_date IS 'original date as in ingest

FORMAT ''YYYY-MM-DD''

the given_xxx attributes serve two purposes:
1) safety: store vital information on the data in case of majore database corruption
2) preservation: since taxon attribution may change over time, original information is presered here.';

CREATE TABLE fiona.autopsy ( 
	id                   serial  NOT NULL,
	population_id        integer  NOT NULL,
	ingest_id            integer  NOT NULL,
	sex                  varchar(140)  ,
	length_total         float8  ,
	length_st            float8  ,
	mass_total           float8  ,
	mass_sh              float8  ,
	remark               varchar(500)  ,
	CONSTRAINT autopsy_pk PRIMARY KEY ( id )
 );

CREATE INDEX idx_autopsy ON fiona.autopsy ( population_id );

CREATE INDEX idx_autopsy_0 ON fiona.autopsy ( ingest_id );

COMMENT ON TABLE fiona.autopsy IS 'Autopsy of individual organisms.
BenDa::Bmess';

COMMENT ON COLUMN fiona.autopsy.id IS '[PK] Unique identifier

UNIT NONE
REFERENCE BenDa::Bmess::BmessID';

COMMENT ON COLUMN fiona.autopsy.population_id IS '[PFK] Associated population.populationid

UNIT NONE
REFERENCE BenDa::Bmess::BcatchID';

COMMENT ON COLUMN fiona.autopsy.sex IS 'Sex of individual


REFERENCE BenDa::Bmess::Sex
FIXME Sex, either male (m) or female (f).';

COMMENT ON COLUMN fiona.autopsy.length_total IS 'Total length of animal (longest extension of animal: fish = body length, crabs = carapax width, shrimps = body length etc.)

UNIT cm
REFERENCE BenDa::Bmess::LengthTotal';

COMMENT ON COLUMN fiona.autopsy.length_st IS 'Standard length of fish: from head to beginning of tail

UNIT cm
REFERENCE BenDa::Bmess::LengthSt';

COMMENT ON COLUMN fiona.autopsy.mass_total IS 'Total mass of animal

UNIT g
REFERENCE BenDa::Bmess::WeightTotal';

COMMENT ON COLUMN fiona.autopsy.mass_sh IS 'Slaughtery mass of fish, i.e. without intestines

UNIT g
REFERENCEBenDa::Bmess::WeightSh';

COMMENT ON COLUMN fiona.autopsy.remark IS 'Beschreibung

REFERENCE BenDa::Bmess::Remark';

ALTER TABLE fiona.autopsy ADD CONSTRAINT fk_autopsy FOREIGN KEY ( population_id ) REFERENCES fiona.population( id );

COMMENT ON CONSTRAINT fk_autopsy ON fiona.autopsy IS '';

ALTER TABLE fiona.autopsy ADD CONSTRAINT fk_autopsy_0 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_autopsy_0 ON fiona.autopsy IS '';

ALTER TABLE fiona.cruise ADD CONSTRAINT fk_cruise FOREIGN KEY ( positioningsystem_id ) REFERENCES fiona.positioningsystem( id );

COMMENT ON CONSTRAINT fk_cruise ON fiona.cruise IS '';

ALTER TABLE fiona.cruise ADD CONSTRAINT fk_cruise_1 FOREIGN KEY ( ship_id ) REFERENCES fiona.ship( id );

COMMENT ON CONSTRAINT fk_cruise_1 ON fiona.cruise IS '';

ALTER TABLE fiona.cruise ADD CONSTRAINT fk_cruise_2 FOREIGN KEY ( lead_person_id ) REFERENCES fiona.person( id );

COMMENT ON CONSTRAINT fk_cruise_2 ON fiona.cruise IS '';

ALTER TABLE fiona.cruise ADD CONSTRAINT fk_cruise_0 FOREIGN KEY ( crs_id ) REFERENCES fiona.crs( id );

COMMENT ON CONSTRAINT fk_cruise_0 ON fiona.cruise IS '';

ALTER TABLE fiona.cruise ADD CONSTRAINT fk_cruise_3 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_cruise_3 ON fiona.cruise IS '';

ALTER TABLE fiona.dataset ADD CONSTRAINT fk_dataset FOREIGN KEY ( contact_person_id ) REFERENCES fiona.person( id );

COMMENT ON CONSTRAINT fk_dataset ON fiona.dataset IS '';

ALTER TABLE fiona.population ADD CONSTRAINT fk_population_0 FOREIGN KEY ( sample_id ) REFERENCES fiona.sample( id );

COMMENT ON CONSTRAINT fk_population_0 ON fiona.population IS '';

ALTER TABLE fiona.population ADD CONSTRAINT fk_population_1 FOREIGN KEY ( sieve_id ) REFERENCES fiona.sieve( id );

COMMENT ON CONSTRAINT fk_population_1 ON fiona.population IS '';

ALTER TABLE fiona.population ADD CONSTRAINT fk_population_2 FOREIGN KEY ( lifestage_id ) REFERENCES fiona.lifestage( id );

COMMENT ON CONSTRAINT fk_population_2 ON fiona.population IS '';

ALTER TABLE fiona.population ADD CONSTRAINT fk_population_3 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_population_3 ON fiona.population IS '';

ALTER TABLE fiona.population ADD CONSTRAINT fk_population FOREIGN KEY ( taxon_id ) REFERENCES fiona.taxon( id );

COMMENT ON CONSTRAINT fk_population ON fiona.population IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample FOREIGN KEY ( station_id ) REFERENCES fiona.station( id );

COMMENT ON CONSTRAINT fk_sample ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_1 FOREIGN KEY ( responsible_person_id ) REFERENCES fiona.person( id );

COMMENT ON CONSTRAINT fk_sample_1 ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_2 FOREIGN KEY ( gear_id ) REFERENCES fiona.gear( id );

COMMENT ON CONSTRAINT fk_sample_2 ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_3 FOREIGN KEY ( status_id ) REFERENCES fiona.status( id );

COMMENT ON CONSTRAINT fk_sample_3 ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_0 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_sample_0 ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_4 FOREIGN KEY ( dataset_id ) REFERENCES fiona.dataset( id );

COMMENT ON CONSTRAINT fk_sample_4 ON fiona.sample IS '';

ALTER TABLE fiona.sample ADD CONSTRAINT fk_sample_5 FOREIGN KEY ( scope_id ) REFERENCES fiona."scope"( id );

COMMENT ON CONSTRAINT fk_sample_5 ON fiona.sample IS '';

ALTER TABLE fiona.sediment ADD CONSTRAINT fk_sediment FOREIGN KEY ( sample_id ) REFERENCES fiona.sample( id );

COMMENT ON CONSTRAINT fk_sediment ON fiona.sediment IS '';

ALTER TABLE fiona.sediment ADD CONSTRAINT fk_sediment_0 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_sediment_0 ON fiona.sediment IS '';

ALTER TABLE fiona.sieveanalysis ADD CONSTRAINT fk_sieveanalysis FOREIGN KEY ( sample_id ) REFERENCES fiona.sample( id );

COMMENT ON CONSTRAINT fk_sieveanalysis ON fiona.sieveanalysis IS '';

ALTER TABLE fiona.sieveanalysis ADD CONSTRAINT fk_sieveanalysis_0 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_sieveanalysis_0 ON fiona.sieveanalysis IS '';

ALTER TABLE fiona.station ADD CONSTRAINT fk_station_0 FOREIGN KEY ( status_id ) REFERENCES fiona.status( id );

COMMENT ON CONSTRAINT fk_station_0 ON fiona.station IS '';

ALTER TABLE fiona.station ADD CONSTRAINT fk_station_1 FOREIGN KEY ( responsible_person_id ) REFERENCES fiona.person( id );

COMMENT ON CONSTRAINT fk_station_1 ON fiona.station IS '';

ALTER TABLE fiona.station ADD CONSTRAINT fk_station FOREIGN KEY ( cruise_id ) REFERENCES fiona.cruise( id );

COMMENT ON CONSTRAINT fk_station ON fiona.station IS '';

ALTER TABLE fiona.station ADD CONSTRAINT fk_station_2 FOREIGN KEY ( ingest_id ) REFERENCES fiona.ingest( id );

COMMENT ON CONSTRAINT fk_station_2 ON fiona.station IS '';

