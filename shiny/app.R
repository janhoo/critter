####           FRONTMATTER           ####
# @Author: Jan M Holstein 
# @Date: "Fri Nov 10 17:53:13 2017"
# @Email: janmholstein@gmail.com
# @Last: "Nov 01 09:03:51 2017"


library(rlang)
library(plyr)
library(dplyr)
library(xtable)
library(leaflet)
library(RColorBrewer)
library(ggplot2)
#library(webshot)
library(htmlwidgets)
library(googleVis)

# ______________________________________________________
# Konstanten
# ______________________________________________________

# Aggregationslevel
t_fields <- c(Genus="taxon.genus",
              Family="taxon.family", 
              Order="taxon.ordnung",
              Class="taxon.klasse",
              Phylum="taxon.phylum",
              Kingdom="taxon.kingdom")

taxon_fields <- factor(
  t_fields,
  levels = t_fields,
  ordered=TRUE)

choices_checkbox<-list("Biomass", "Abundance")

# ______________________________________________________
# Funktionen ####
# ______________________________________________________

# Link Google Suche
create.Glink <- function(val) {
  sprintf('<a href="https://www.google.com/#q=%s" target="_blank" class="btn btn-primary btn-xs">Google</a>',val)
}

# Wrap HTML-Link
wrap.link <- function(link, name, btn = "btn btn-primary btn-xs") {
  paste0("<a href=\"",link,"\" target=\"_blank\" class=\"",btn,"\" >",name,"</a>")
}

# Hole den Name eines Wertes 
get.cname <- function(cvector, value){
  return (names(cvector)[match(value,cvector)])
} 

# Nice doi
make.nice.doi <- function(y, ...){
  sapply(y,function(x){
    if (is.na(x)){
      return(NA)
    } 
    if (is.na(stringr::str_locate(x, "http")[1])){
      wrap.link(paste0("https://doi.org/",x),"DOI", ...)
    } else {
      wrap.link(x,"DOI", ...)
    }
  })
}

# Signifikante Stellen
sigDigits <- function(y,d){
  sapply(y,function(x,di){
    z <- format(x,digits=di)
    if (!grepl("[.]",z)) return(z)
    require(stringr)
    return(str_pad(z,di+1,"right","0"))
  },d)
}

# Pie Chart
pieChart <- function(x,sample_id,param,title,treshold=0.01){
  # print("---------------------")
  # print("PIE-CHART")
  # print(paste("title:  ",title))
  # print(paste("smpl_id:",sample_id))
  # print(paste("data:   ",nrow(x)))
  # print("---------------------")
  param_s<-sym(param)
  y <- x %>% ungroup() %>% filter(population.sample_id==sample_id) %>%
    arrange(desc(!!param_s)) %>%
    mutate(x=as.numeric(sapply(!!param_s,sigDigits,d=2))) %>%
    select(taxon.taxon,x) %>%
    rename(taxon = taxon.taxon,
           parameter = x)
  # Wenn keine Eintraege vorhanden -> raus
  if (all(is.na(y$parameter))){
    return(NULL)
  }
  return(gvisPieChart(y,options=list(
    title=title,
    sliceVisibilityThreshold=treshold,
    titleTextStyle="{fontName:'Arial' }",
    chartArea = "{left:0,top:20, width:'100%',height:'75%'}"
  ))
  )
}

# Table: Aggregation == all/species
make.species.table <- function(x){
  x %>%
    dplyr::rename( Taxon = taxon.taxon, 
                   Rank = taxon.rank, 
                   Info = taxon.url ) %>%
    dplyr::select(Taxon, Rank, Info) %>% 
    dplyr::mutate(Info = wrap.link(Info,"WORMS")) %>%
    dplyr::arrange(Taxon)  
}

# Table: Aggregation != all/species
make.taxon.table <- function(x){
  x %>%
    dplyr::rename( Taxon = taxon.taxon) %>%
    dplyr::select(Taxon) %>% 
    dplyr::mutate(Info = create.Glink(Taxon)) %>%
    dplyr::arrange(Taxon)
}

# Table: General
make.general.table <- function(x){
  
  x %>%
    #distinct(population.sample_id) %>% 
    dplyr::rename(
      Dataset = dataset.name, 
      Lineage = dataset.lineage,
      Date = sample.start_on, 
      Cruise = cruise.name, 
      Ship = ship.name,
      Sample = sample.name, 
      Lon = sample.start_lon, 
      Lat = sample.start_lat, 
      Gear = gear.type,
      "Gear Cat." = gear.category,
      Depth = gebco14.depth,
      Scope = scope.name,
      "av. Rank" = tot.av_rank,
      Richness = tot.population.richness,
      Info = dataset.doi) %>%
    dplyr::select(Dataset, Date, Lineage, Cruise,Ship, Sample, Lon, Lat, 
                  Gear, "Gear Cat.", Depth, Scope, "av. Rank",
                  Richness, Info) %>% 
    dplyr::mutate(Info = make.nice.doi(Info),
                  Date = format(Date, format="%Y-%m-%d")) %>%
    t() %>%
    `colnames<-`(HTML("<br>")) # TWEAK -> ich zwinge hier mittels HTML einen Break in Colum-Header 1 -> damit beide Sample-Tabellen horizontal bündig ausgerichtet sind
}

# Isoliere Sample
select.sample <- function(x,id) {
  filter(x, population.sample_id == id) 
} 

# Ermittle Auswahl von GUI-Elementen
choices_subset <- function(x){
  x.list<-list()
  x.list<-append(x.list,list(choices_taxon=as.list(c("All",levels(factor(x$taxon.valid_name))))))
  x.list<-append(x.list,list(choices_dataset=as.list(c(levels(factor(x$dataset.name))))))
  x.list<-append(x.list,list(choices_gear=as.list(c(levels(factor(x$gear.category))))))
  x.list<-append(x.list,list(choices_region=as.list(c(levels(factor(x$cruise.region))))))
  x.list<-append(x.list,list(choices_daterange=c(min(x$sample.start_on),max(x$sample.start_on))))
  x.list<-append(x.list,list(choices_aggregate=as.list(c(All="All",Species="Species",t_fields))))
  x.list<-append(x.list,list(choices_scope=as.list(c(levels(factor(x$scope.name))))))
  return(x.list)
}

# Primärfilter
primary.filter <- function(x, daterange=c(min(x$sample.start_on),max(x$sample.start_on)), taxon="All", gear=NULL, region=NULL, dataset=NULL, scope=NULL, minrich=0, maxrich=max(x$tot.population.richness), mass=FALSE, abundance=FALSE){
  stopifnot(inherits(x,"data.frame"))
  stopifnot(inherits(x$sample.start_on,"Date"))
  x %>%
    filter(sample.start_on >= min(daterange) & sample.start_on <= max(daterange)) %>%
    filter(taxon.valid_name == taxon | taxon == "All" |  is.null(taxon)) %>%
    filter(gear.category %in% gear) %>%
    filter(cruise.region %in% region) %>% 
    filter(dataset.name %in% dataset) %>%
    filter(scope.name %in% scope) %>%
    filter(tot.population.richness >= minrich & tot.population.richness <= maxrich ) %>%
    filter(!(is.na(tot.population.biomass_wet) & mass)) %>%
    filter(!(is.na(tot.population.number) & abundance)) %>%
    filter(tot.population.richness>=minrich)
}

# Filter: Aggregiere Taxa
aggregate.taxon <- function(x, group_var){
  stopifnot(group_var %in% c("All","Species",names(taxon_fields)))
  stopifnot(inherits(x,"data.frame"))
  # Hilfsfkt1: Aggregation ueber Taxa
  taxon.aggregate <- function(x, group_var){
    group_var <- sym(group_var)
    left_join(
      x %>%
        group_by(population.sample_id,!!group_var) %>%
        dplyr::summarise(taxon.population.number = sum(population.number,na.rm = TRUE), 
                         taxon.population.biomass_wet = sum(population.biomass_wet,na.rm = TRUE),
                         taxon.population.richness = n(),
                         taxon.population.shannonwiener = (-1) * sum(taxon.population.number/sum(taxon.population.number,na.rm = TRUE) * log(taxon.population.number/sum(taxon.population.number,na.rm = TRUE)),na.rm = TRUE)
        )  %>%
        dplyr::mutate(taxon.taxon = !!group_var)  %>% 
        dplyr::ungroup() %>%
        select(-!!group_var) %>%
        dplyr::filter(!is.na(taxon.taxon)) %>%
        mutate(taxon.population.number = ifelse(taxon.population.number<=0,NA,taxon.population.number),
               taxon.population.biomass_wet = ifelse(taxon.population.biomass_wet<=0,NA,taxon.population.biomass_wet),
               taxon.population.richness = ifelse(taxon.population.richness<=0,NA,taxon.population.richness),
               taxon.population.shannonwiener = ifelse(taxon.population.richness<=1,NA,taxon.population.shannonwiener)),
      x %>% distinct(population.sample_id,.keep_all = TRUE),by=c("population.sample_id"="population.sample_id"))
  }
  
  # Hilfsfkt2: Erzeuzge gleiche Attribute wie taxon.ggregate falls keine Aggregation stattgefunden hat
  copy.aggregate <- function(x){
    x %>% mutate(taxon.taxon = taxon.valid_name,
                 taxon.population.number = population.number,
                 taxon.population.biomass_wet = population.biomass_wet,
                 taxon.population.richness = taxon.population.number,
                 taxon.population.shannonwiener = tot.population.shannonwiener)
  }
  
  # Aggregation
  return(
    switch(group_var,
           "All" = {copy.aggregate(x)},
           "Species" = {x %>% filter(taxon.rank <= group_var) %>% copy.aggregate},
           {x %>% taxon.aggregate(as.character(taxon_fields[group_var]))}
    ))
}

# Aggregate data per Sample (for plotting) 
make.samples <- function(x){
  stopifnot(inherits(x,"data.frame"))
  x %>%
    distinct(population.sample_id,.keep_all = TRUE)
}

# Table: Info für Datasets in Karte
make.datasets.table <- function(x){
  left_join(
    group_by(x,sample.dataset_id) %>%
      dplyr::summarize(samples=n(),
                       avg_richness=mean(tot.population.richness, na.rm = TRUE)
      ), x %>%
      distinct(sample.dataset_id, .keep_all = TRUE)
    , by=c("sample.dataset_id"="sample.dataset_id")
  ) %>%
    mutate(avg_richness = sigDigits(avg_richness,1)) %>%
    dplyr::rename(Dataset = dataset.name,
                  Info = dataset.doi,
                  Lineage = dataset.lineage,
                  Realm = dataset.realm,
                  Contact = dataset.reference_person,
                  Mail = person.email,
                  "No. Samples" = samples,
                  "av. Richness" = avg_richness) %>%
    mutate(Info = make.nice.doi(Info)) %>% 
    mutate(Contact = ifelse (! is.na(Mail), paste("<a href = mailto:",Mail,">",Contact,"</a>", sep=""), Contact)) %>%
    dplyr::select(Dataset,
                  Info,
                  Lineage,
                  Realm,
                  Contact,
                  "No. Samples",
                  "av. Richness") 
}

# color
colpal<-function(func="colorNumeric",palette="YlOrRd",domain){
  switch(func,
         colorQuantile = {colorQuantile(	palette = palette, domain = domain, na.color = "#808080" )},
         colorNumeric = {colorNumeric(	palette = palette, domain = domain, na.color = "transparent" )},
         colorBin = {colorBin(	palette = palette, domain = domain, na.color = "#808080" )},
         {colorBin(	palette = palette, domain = domain, na.color = "#808080" )}  )
}
get.df.feature <- function(x,name){
  x[[name]]
}

# Ausgelagerte Funktionen
#source("getData.R") # Methoden zum aktiven Erzeugen des critter-Dataframe aus der Datenbank (brauchen wir noch nicht)
#source("func.R", local = TRUE)

# ______________________________________________________
# Initialisierungen   #####
# ______________________________________________________

# System
#rm(list=ls()) # Leere den Speicher
#setwd("/scratch/users/pkloss/git/visualizer") # Setze das Arbeitsverzeichnis (sollte später automatisch ermittelt werden)

# Info
print("* Initialisierung")
print(paste("Aktuelles Arbeitsverzeichnis:",getwd()))

# Hole alle Critter-Daten
#cdata <- getWholeCritterData() # ... aktiv aus DB oder DB-Mirror
cdata <- readRDS(file="./data/arctic_new.rds") # ... direkt aus Datei

# Ermittle Standardauswahl von GUI-Elementen
choices_default <- choices_subset(cdata)

# color
choices_parameter<-as.list(c(Default="default",
                             Richness="tot.population.richness",
                             "Shannon-Wiener"="tot.population.shannonwiener",
                             Abundance="tot.population.number",
                             Biomass="tot.population.biomass_wet"
))


# ______________________________________________________
# Server ####
# ______________________________________________________

print("* Baue Shiny-Server auf")

server = function(input, output, session) {
  
  # ______________________________________________________
  # Reactive Values/Functions ####
  # ______________________________________________________
  
  # Update AuswahlanzahlMultiselection (Dataset, Region, ...)
  update.filter.info.multiselect <- function(){
    
    # Dataset
    dataset_akt <- length(input$einDataset)
    dataset_max <- length(choices_default$choices_dataset)
    dataset_info <- paste("(",dataset_akt,"/",dataset_max,")", sep ="")
    output$dataset_auswahl_info <- renderText(dataset_info)
    
    # Region
    region_akt <- length(input$einRegion)
    region_max <- length(choices_default$choices_region)
    region_info <- paste("(",region_akt,"/",region_max,")", sep ="")
    output$region_auswahl_info <- renderText(region_info)
    
    # Gear
    gear_akt <- length(input$einGear)
    gear_max <- length(choices_default$choices_gear)
    gear_info <- paste("(",gear_akt,"/",gear_max,")", sep ="")
    output$gear_auswahl_info <- renderText(gear_info)
    
    # Scope
    scope_akt <- length(input$einScope)
    scope_max <- length(choices_default$choices_scope)
    scope_info <- paste("(",scope_akt,"/",scope_max,")", sep ="")
    output$scope_auswahl_info <- renderText(scope_info)
    
  }
  
  # Angeklickter Punkt auf Karte 
  mapClickedPoint <- reactiveVal(NULL)
  clicker<-reactiveVal(NULL)
  
  # Tabellen/Torten  Statistik
  tableGeneral <- reactiveVal(NULL)
  tableTaxa <- reactiveVal(NULL)
  tableShownDatasets <- reactiveVal(NULL)
  tableFilterConfig <- reactiveVal(NULL)
  
  pieChartTaxa <- reactiveVal(NULL)
  #pieSpecies <- reactiveVal(NULL)
  
  # Primärfilter
  dataFiltered <- reactive({
    mass<-ifelse(
      is.null(input$checkGroup),
      FALSE,
      "Biomass"%in% input$checkGroup
    )
    abundance<-ifelse(
      is.null(input$checkGroup),
      FALSE,
      "Abundance"%in% input$checkGroup
    )
    
    # Filterinfos aktualisieren
    update.filter.info.multiselect()
    
    primary.filter(
      x = cdata, 
      daterange = c(input$einZeitraum[1],input$einZeitraum[2]), 
      taxon = input$einTaxon, 
      gear = input$einGear, 
      region = input$einRegion, 
      dataset = input$einDataset,
      scope = input$einScope,
      mass = mass,
      abundance = abundance,
      minrich = input$num)
  })
  
  # Aggregation
  dataAggregated <- reactive({
    aggLevelname  <- get.cname(choices_default$choices_aggregate,input$einAggregationslevel)
    aggregate.taxon(x = dataFiltered(), group_var = aggLevelname)
  })
  
  # Reduziere Daten auf (unterschiedliche, anhand der Sample-ID) Samples  
  dataSampleized <- reactive({
    isolate(saveClick <- clicker())
    samples <- make.samples(dataAggregated())

    print("* Primärauswahl wurde veraendert")
    print("Berechne neue Samples")
    print(paste("Clicker Null:",is.null(saveClick)))
    print(paste("Clicker-ID in Samples:", saveClick$id %in% samples$population.sample_id))
  
    # Ist CLicker-Id noch in gefilterten Daten? -> Clicker nicht Löschen
    if (is.null(saveClick)) {
      return (samples)
    } else if (saveClick$id %in% samples$population.sample_id){
      return(samples) 
    }
    print("Clicker wurde geloescht")
    clicker(NULL)
    return(samples)
  })
  
  # Ueberwache Klick auf Karte (nicht Marker)
  observe({
    print("* Klick neben Karte")
    print("Loesche Clicker, alle Tabellen, Charts")
    input$karte_click
    tableGeneral(NULL)
    tableTaxa(NULL)
    pieChartTaxa(NULL)
    clicker(NULL)
    leafletProxy("karte", session = session) %>% clearPopups() 
  })
  
  # ______________________________________________________
  # Observer ####
  # ______________________________________________________
  
  # Toggle-Button: (De-)Select all Datasets
  observeEvent(input$btn_toggle_dataset_selectall, {
    if (is.null(input$einDataset))
      region_toggle <- choices_default$choices_dataset
    else 
      region_toggle <- NULL
    updateCheckboxGroupInput(session = session, inputId = "einDataset", choices = choices_default$choices_dataset , selected = region_toggle)
  })
  
  # Toggle-Button: (De-)Select all Regions
  observeEvent(input$btn_toggle_region_selectall, {
    if (is.null(input$einRegion))
      region_toggle <- choices_default$choices_region
    else 
      region_toggle <- NULL
    updateCheckboxGroupInput(session = session, inputId = "einRegion", choices = choices_default$choices_region , selected = region_toggle)
  })
  
  # Toggle-Button: (De-)Select all Gaers
  observeEvent(input$btn_toggle_gear_selectall, {
    if (is.null(input$einGear))
      region_toggle <- choices_default$choices_gear
    else 
      region_toggle <- NULL
    updateCheckboxGroupInput(session = session, inputId = "einGear", choices = choices_default$choices_gear , selected = region_toggle)
  })
  
  # Toggle-Button: (De-)Select all Scopes
  observeEvent(input$btn_toggle_scope_selectall, {
    if (is.null(input$einScope))
      region_toggle <- choices_default$choices_scope
    else 
      region_toggle <- NULL
    updateCheckboxGroupInput(session = session, inputId = "einScope", choices = choices_default$choices_scope , selected = region_toggle)
  })
  
  # Ueberwache Primärfilter: Bei Veraenderung -> Passe Tabelleninhalte an  
  observe({
    print("* Samples wurden veraendert")
    print("Erzeuge alle Tabellen neu")
    # Erzeuge neue Tabelle ueber aktuell auf der Karte angezeigten Datasets 
    tableShownDatasets(make.datasets.table(dataSampleized()))
    tableGeneral(NULL)
    tableTaxa(NULL)
    tableFilterConfig(
      data.frame(
        "Date Range" = paste(input$einZeitraum[1],"-",input$einZeitraum[2]),
        "Dataset" = paste(input$einDataset, collapse=", "),
        "Region" = paste(input$einRegion, collapse=", "),
        "Gear" = paste(input$einGear, collapse=", "),
        "Taxon" = input$einTaxon,
        "Aggregationslevel" = get.cname(choices_default$choices_aggregate,input$einAggregationslevel),
        "Richness" = input$num
      ) %>% t()
    )
    
    # Popups löschen
    #leafletProxy("karte", session = session) %>% clearPopups() 
    
  })
  
  # Ueberwache Color-Mapping
  co <- reactiveValues(pal = NULL, radius = 4, stroke = TRUE,color = "#03F", weight = 5, opacity = 0.5, fill = TRUE, fillColor = "#03F", fillOpacity = 0.2)
  feature <- reactive({
    get.df.feature(x=dataSampleized(),name=input$einParameter)
  })
  # pal <- reactive({
  #   colpal(domain=feature())
  # 
  # })
  observe({
    
    # palette <- brewer.pal(5, "Spectral")
    # previewColors(colorNumeric(palette = palette, domain = 1:5), values = 1:5)
    # 
    #print(input$einParameter)
    if(input$einParameter%in%c("tot.population.number",
                               "tot.population.biomass_wet",
                               "tot.population.richness",
                               "tot.population.shannonwiener")){
      func<-"colorBin"
      palette<-rev(brewer.pal(5, "Spectral"))
    } else if (input$einParameter%in%c("dataset.name")){
      func<-"colorFactor"
      palette<-"Set3"
    } 
    tryCatch(
      {
        co$pal <- colpal(func=func,palette=palette,domain=feature())
        co$radius <- 4 
        co$stroke <- TRUE
        co$color <- co$pal(feature())
        co$weight <- 5
        co$opacity <- 0.5
        co$fill <- TRUE
        co$fillColor <- co$pal(feature())
        co$fillOpacity <- 0.6
      },
      warning = function(war) {print("warnings were produced")},
      error = function(err) {
        print("palette failed!")
        co$radius <- 4
        co$stroke <- TRUE
        co$color <- "#03F"
        co$weight <- 5
        co$opacity <- 0.5
        co$fill <- TRUE
        co$fillColor <- "#03F"
        co$fillOpacity <- 0.5
      }
      
    )
  })
  observe({
    if (is.null(feature())){
      return()}
    leafletProxy("karte") %>% 
      clearControls() %>%
      addLegend(pal = co$pal, values = feature())
    
  })
  
  # Ueberwache Klick auf einen Marker: Veraenderung -> Speichere Wert reaktive Value 
  observe({
    print("* Click auf einen Marker")
    clicker(input$karte_marker_click)
  })
  
  # Ueberwache reaktive Value fuer Klick auf Marke/Karte Clicker()
  observe({
    print("* Clicker wurde veraendert")
    # Click holen und sichern
    saveClick <- clicker()
    
    # Clicker ist Null (gesetzt worden) -> Popups loeschen -> Ende
    if (is.null(saveClick)){
      print("CLicker ist Null -> Loesche Popups")
      # Popup -Eintrag-> Karte
      map <- leafletProxy("karte", data = dataSampleized()) # Map-Proxy
      map %>% 
        clearPopups()
      return()
    }
    
    # Info
    showNotification(id = "click", closeButton = FALSE, "Loading point data ...")
    
    # Ausgewaehlte Datensaetze
    pop.sel <- select.sample(dataAggregated(), saveClick$id) # alle durch Klick ausgewählten Populationen (besitzen alle die selbe sample.id)
    pop.sel.first = pop.sel[1,]
    
    # Erzeuge PieChart-Dataframe
    pieChartTaxa(pop.sel) 
    
    # Speicher Selected DF 
    mapClickedPoint(pop.sel)
    
    # Erzeuge Tabelleninhalt fuer allgemeine Informationen zu angeklicktem Punkt (Sample)
    tableGeneral(make.general.table(pop.sel[1,]))
    
    # Erzeuge Tabelleninhalt fuer Populationssnformationen zu angeklicktem Punkt (Sample)
    tt <- if (any(c("All","Species") %in% input$einAggregationslevel)){
      # Aggregation == all/species
      make.species.table(pop.sel)
    } else {
      # Aggregation != all/species
      make.taxon.table(pop.sel)
    }
    tableTaxa(tt)
    
    # Popup-Text
    text.pop <- paste("<b>Dataset:", pop.sel.first$dataset.name, "</b><br>Cruise:", pop.sel.first$cruise.name, "<br>Date:", pop.sel.first$sample.start_on, "<br>Info:", make.nice.doi(pop.sel.first$dataset.doi,btn=""))
    
    # Popup -Eintrag-> Karte
    map <- leafletProxy("karte", data = dataSampleized()) # Map-Proxy
    map %>% 
      clearPopups() %>% 
      addPopups(lng = saveClick$lng, lat = saveClick$lat, text.pop)
    
    # Info aus
    removeNotification(id = "click")
  })
  
  # Ueberwache Samples -> Veraenderung -> Punkte neu in Karte eintragen
  observe({
    print("* Samples oder Projektionsart ist veraendert worden")
    print("Trage neue Punkte in Karte ein")
    projektionR() # TWEAK: Wird Projektionsart veraendert -> Punkte neu in Karte eintragen
    data <- dataSampleized()
    map <- leafletProxy("karte", data = data)
      map  %>% clearMarkers() %>%
        addCircleMarkers( radius=co$radius, stroke = co$stroke, fillOpacity = co$fillOpacity, color = co$color,weight=co$weigth, opacity = co$opacity, fill = co$fill, fillColor = co$fillColor, lng =~sample.start_lon, lat =~sample.start_lat, layerId =~ population.sample_id)
  })
  
  # ______________________________________________________
  # Output ####
  # ______________________________________________________
  
  # Projektionsart
  # Variable
  output$projektion <- renderText({input$einProjektion})
  # Reaktive Methode
  projektionR <- reactive({
    print("*Projektionsart veraendert")
    print("Reset Clicker, Sample-Tabellen")
    # Tweak: Wird die Projektionsart veraendert -> Reset angeklickte Samples (CLicker, Tabellen)
    clicker(NULL) 
    tableGeneral(NULL)
    tableTaxa(NULL)
    
    # Veraendere Projektion
    projektion <- input$einProjektion
  })
  
  #
  # Allgemeine Statistik zur Karte
  #
  output$statistik  <- renderTable(
    {data.frame(Auswertung=c("No. of entries in database", "No. of entries shown", "No. of samples shown"),Wert=c(nrow(cdata),nrow(dataAggregated()),nrow(dataSampleized())))}, 
    colnames = FALSE, 
    rownames = FALSE
  )
  
  # Statistik zur Karte: Informationen über alle angezeigten Datasets
  output$statShownDatasets <- renderDataTable(
    tableShownDatasets(), escape = FALSE
  )
  
  # Info zur Filtereinstellung
  output$filterConfig <- renderTable(
    tableFilterConfig(), 
    colnames = FALSE,
    rownames = TRUE,
    escape = FALSE
  )
  
  # Allgemeine Informationen zu angeklicktem Punkt (Sample)
  output$infoClickedPoint  <- renderTable(
    tableGeneral(), 
    colnames = TRUE,
    rownames = TRUE,
    sanitize.text.function = function(x) x
  )
  
  # Populationsinformationen zu zu angeklicktem Punkt (Sample)
  output$infoClickedPointTaxa <-renderTable(
    tableTaxa(),
    colnames = TRUE,
    rownames = FALSE,
    sanitize.text.function = function(x) x)  
  
  # Erzeuge Pie-Charts
  output$widgetPieChartTaxaNum <- renderGvis(
    if (is.null(pieChartTaxa())){
      NULL
    } else {
      saveClick <- clicker()
      if (is.null(saveClick)){
        return()
      }
      pieChart(pieChartTaxa(), saveClick$id, "taxon.population.number", title = 'Abundance')
    }
  )
  output$widgetPieChartTaxaMass <- renderGvis(
    if (is.null(pieChartTaxa())){
      NULL
    } else {
      saveClick <- clicker()
      if (is.null(saveClick)){
        return()
      }
      pieChart(pieChartTaxa(), saveClick$id, "taxon.population.biomass_wet", title = 'Biomass [g/sqrm]')      
    }
  ) 
  
  # Karte
  output$karte <- renderLeaflet({
    
    # gefilterte Daten holen
    
    showNotification(id = "filter", closeButton = FALSE, duration=0.5, "Filtering data ...")
    #data <- dataSampleized()
    
    # Karte je nach gewählter Projektionsart aufbauen
    showNotification(id = "karte", closeButton = FALSE, duration=0.5, "Building Map ...")
    
    # FIXME: Tweak (keine Daten -> Projektion auf MErcator umstellen)
    projektion <- projektionR()
    # if (nrow(data) == 0){
    #   updateCheckboxInput(session, "einProjektion", value = "Mercator")
    #   projektion <- "Mercator"
    # }
    
    if (projektion == "Arctic") {
      # Arktis
      # Initialisierung
      extent <- 11000000 + 9036842.762 + 667
      #extent <- 5037510
      origin = c(-extent, extent)
      #origin = c(0, 90)
      maxResolution <- ((extent - -extent) / 256)
      bounds <- list(c(-extent, extent),c(extent, -extent))
      minZoom <- 0
      maxZoom <- 18
      defZoom <-4
      resolutions <- purrr::map_dbl(minZoom:maxZoom,function(x) maxResolution/(2^x))
      #resolutions <- c(8192, 4096, 2048, 1024, 512, 256)
      crsArtic <- leafletCRS(
        crsClass = 'L.Proj.CRS',
        code = 'EPSG:3571',
        proj4def = '+proj=laea +lat_0=90 +lon_0=180 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs',
        resolutions = resolutions,
        origin = origin,
        bounds = bounds
      )
      # Leaflet
      l <- leaflet(options= leafletOptions(crs=crsArtic))
      l <- setView(l, 0,90, defZoom)
      l <- addTiles(l, urlTemplate = "http://{s}.tiles.arcticconnect.org/osm_3571/{z}/{x}/{y}.png",attribution = "Map © ArcticConnect. Data © OpenStreetMap contributors", options = tileOptions(subdomains = "abc", noWrap = TRUE,continuousWorld = FALSE)) 
      l <- addGraticule(l)
      
    } else {
      # Mercator
      l <- leaflet(options=leafletOptions(minZoom = 1))
      l <- addProviderTiles(l, "Esri.NatGeoWorldMap")
    }
    
    # Daten in Karte eintragen 
    # if (nrow(data) != 0){
    #   #l <- addCircleMarkers(l, radius=1, lng =~sample.start_lon, lat =~sample.start_lat, layerId =~ population.sample_id)
    #   l <- addCircleMarkers(l, radius=co$radius, stroke = co$stroke, fillOpacity = co$fillOpacity, color = co$color,weight=co$weigth, opacity = co$opacity, fill = co$fill, fillColor = co$fillColor, lng =~sample.start_lon, lat =~sample.start_lat, layerId =~ population.sample_id)
    # }
    
    # Leaflet-Objekt der Karte (global) merken fuer Kartendownload
    karte_leaflet <<- l
    
    # Karte zurueckgeben
    l
  })
  
  # Download (Csv)
  output$downloadDataCsv <- downloadHandler(
    filename = function() {
      paste("data-", Sys.Date(), ".csv", sep="")
    },
    content = function(file) {
      write.csv(dataFiltered(), file)
    }
  )
  
  # Erzeuge Downloadnamen (Csv)
  output$fname <- renderText({
    paste("Download critter-subset-", Sys.Date(), ".csv", sep="")
  })
  
  # Download Filtereinstellung 
  output$downloadFilterConf <- downloadHandler(
    filename = "filter.txt",
    content = function(file) {
      write.table(quote = FALSE, tableFilterConfig(), file)
    }
  )
  
  # Download Map 
  output$downloadMap <- downloadHandler(
    filename = "map.png",
    content = function(file) {
      # Speichere Temp Html-File
      home_tmp_map <- paste(Sys.getenv("HOME"),"/map_temp.html",sep = "")
      saveWidget(karte_leaflet, home_tmp_map, selfcontained = FALSE)
      # Konvertiere in PNG
      webshot(home_tmp_map, file=file, cliprect = 'viewport')
    }
  )
  
  # Histograme 
  output$histogramDepth <- renderPlot({
    ggplot(dataSampleized(), aes(gebco14.depth)) + geom_histogram(binwidth = 10) + xlab("Depth") + ylab("Samples")}, 
    height = 200
  )
  output$histogramPop <- renderPlot({
    ggplot(dataSampleized(), aes(tot.population.richness)) + geom_histogram(binwidth = 1) + xlab("Richness") + ylab("Samples")}, 
    height = 200
  )
  
  # Zeitraum
  output$zeitraum  <- renderText({paste(input$einZeitraum[1],"-",input$einZeitraum[2])})
  
  # Gear
  output$gear  <- renderText({input$einGear})
  
  # Taxon
  output$taxon  <- renderText({input$einTaxon})
  
  # Aggregationslevel
  output$aggregationslevel <- renderText({
    get.cname(choices_default$choices_aggregate,input$einAggregationslevel)
  })
  
  # Dataset
  output$dataset  <- renderText({input$einDataset})
  #output$dataset_auswahl_info <- renderText("hallo")
  
  # Region
  output$region  <- renderText({input$einRegion})
  
  # Scope
  output$scope  <- renderText({input$einScope})
  
  # ?
  output$checkboxparams <- renderText({
    if(is.null(input$checkGroup)) {"None"}
    else  paste(input$checkGroup, collapse=", ")
  })
  
  # ?
  output$radiochoices <- renderText({
    if(is.null(input$radio)) {"None"}
    else  paste(input$radio, collapse=", ")
  })
  
  # ?
  output$richnum <- renderText({
    input$num
  })
  
}

#  ______________________________________________________
# UI ####
#  ______________________________________________________

print("* Baue Shiny-GUI auf")

# <link rel="stylesheet" href="https://fonts.googleapis.com/css?/family=Arvo">

ui = fluidPage(title="Critter",
               
               # CSS-Definitionen
               tags$head(
                 
                 # Fonts
                 tags$link(rel = "stylesheet", type = "text/css", href = "https://fonts.googleapis.com/css?family=Michroma"),
                 
                 # HTML-Tags
                 tags$style(HTML("
                                 
                                 span.rightfloat {
                                 float: right;
                                 }
                                 
                                 div.collapse_style {
                                 border-radius: 4px; 
                                 background-color: white; 
                                 margin: 10px 0px; 
                                 padding: 10px; 
                                 border: 1px solid lightgrey;
                                 word-wrap: break-word;
                                 }
                                 
                                 div.multicol4 { 
                                 column-count: 4;
                                 #-webkit-column-count: 4; # Chrome, Safari, Opera
                                 #-moz-column-count: 4; # Firefox
                                 
                                 #.selectize-input { padding: 2px; min-height: 0; } 
                                 
                                 "))),
               
               # Titel
               titlePanel(
                 
                 tags$div(style = "padding: 10px; border-radius: 4px; text-align:left; background-color: #428bca; font-family: Michroma",
                   tags$img(style="display: inline", src = "crabby.png", height = 50, width = 50),
                   tags$h1(style="display: inline; vertical-align:middle", "Critter" ),

                 
                 div(style = "display: grid; grid-template-columns: 50% 50%",
                     h6("data exploration and retrieval",code(style="diyplay: inline; border-radius: 4px; color: red; background-color: white;","v0.1.05")),
                     h6(style = "text-align: right","Explore Arctic marcobenthos sampling campaigns"))
                    
                  # br(),
                  # div(style = "display: inline;",
                  #     tags$span(style = "float: left; display: inline;",
                  #           tags$h6("data exploration and retrieval", style = "display: inline;"),
                  #           tags$code("v0.1.05", style = "font-size: 25%; display: inline;")),
                  #     tags$span(style = "float: right;",tags$h6("you see here stuff and stuff and stuff..."))
                  # ),
                  # br()
                  
                 )
               ),
               
                
               # Layout
               sidebarLayout(
                 position= "left",
                 # Sidebar
                 sidebarPanel(
                   
                   h3("Data filter"),
                   dateRangeInput("einZeitraum", "Date range", start = choices_default$choices_daterange[1], end = choices_default$choices_daterange[2]),
                   tags$b("Dataset"),
                   tags$span(class="rightfloat",
                             textOutput("dataset_auswahl_info", inline = TRUE),
                             HTML('<button title="show/hide selection" data-toggle="collapse" class="btn btn-primary btn-xs" data-target="#dataset_collapse">&#9660</button>')),
                   tags$div(id = 'dataset_collapse', class="collapse collapse_style", 
                            actionLink("btn_toggle_dataset_selectall","(un)select all"), 
                            checkboxGroupInput("einDataset", label=NULL, choices = choices_default$choices_dataset, selected = choices_default$choices_dataset)), 
                   tags$p(),
                   tags$b("Region"),
                   tags$span(class="rightfloat",
                             textOutput("region_auswahl_info", inline = TRUE),
                             HTML('<button title="show/hide selection" data-toggle="collapse" class="btn btn-primary btn-xs" data-target="#region_collapse">&#9660</button>')),
                   tags$div(id = 'region_collapse', class="collapse collapse_style", 
                            actionLink("btn_toggle_region_selectall","(un)select all"), 
                            checkboxGroupInput("einRegion", label=NULL, choices = choices_default$choices_region, selected = choices_default$choices_region)),
                   tags$p(),
                   tags$b("Gear"),
                   tags$span(class="rightfloat",
                             textOutput("gear_auswahl_info", inline = TRUE),
                             HTML('<button title="show/hide selection" data-toggle="collapse" class="btn btn-primary btn-xs" data-target="#gear_collapse">&#9660</button>')),
                   tags$div(id = 'gear_collapse', class="collapse collapse_style", 
                            actionLink("btn_toggle_gear_selectall","(un)select all"), 
                            checkboxGroupInput("einGear", label=NULL, choices = choices_default$choices_gear, selected = choices_default$choices_gear)),
                   tags$p(),
                   tags$b("Scope"),
                   tags$span(class="rightfloat",
                             textOutput("scope_auswahl_info", inline = TRUE),
                             HTML('<button title="show/hide selection" data-toggle="collapse" class="btn btn-primary btn-xs" data-target="#scope_collapse">&#9660</button>')),
                   tags$div(id = 'scope_collapse', class="collapse collapse_style", 
                            actionLink("btn_toggle_scope_selectall","(un)select all"),
                            checkboxGroupInput("einScope", label=NULL, choices = choices_default$choices_scope, selected = choices_default$choices_scope)),
                   tags$p(),
                   selectizeInput("einTaxon", label="Taxon", choices = choices_default$choices_taxon, options = list(maxOptions = 4000), selected = choices_default$choices_taxon[[1]]),
                   tags$p(),
                   numericInput("num", label = "Samples with richness greater than", value = 0,min = 0 ),
                   tags$p(),
                   fluidRow(
                     column(6,radioButtons("einAggregationslevel",
                                           inline = FALSE, 
                                           label = "Aggregation",
                                           choices = choices_default$choices_aggregate,
                                           selected = "All")),
                     column(6,radioButtons("einParameter", 
                                           inline = FALSE, 
                                           label = "Color",
                                           choices =  choices_parameter, 
                                           selected = choices_parameter[[1]]))
                   ),
                   fluidRow(
                     column(6,checkboxGroupInput("checkGroup", 
                                                 inline = FALSE, 
                                                 label = "Biology", 
                                                 choices = choices_checkbox,
                                                 selected = choices_checkbox[[2]])),
                     column(6,radioButtons("einProjektion",
                                           inline = FALSE,
                                           label = "Projection",
                                           choices = list("Mercator", "Arctic"),
                                           selected = "Arctic")))
                 ),
                 
                 # Mainpanel
                 mainPanel(     
                   
                   # Karte
                   leafletOutput("karte",height = 600),
                   fluidRow(
                     column(6,tableOutput("statistik")),  
                     column(6,tags$span( style = "float: right", "Click points for information on respective sample"))
                   ),
                   downloadLink("downloadDataCsv", textOutput(inline = TRUE, "fname")),
                   "|",
                   # download Map Widget does no function on shiny.io
                   # downloadLink("downloadMap", "map"),
                   # "|",
                   downloadLink("downloadFilterConf", "filter-configuration"),
                   # Infos zu angeklicktetm Sample
                   h3("Information on clicked sample"),
                   tags$div( style = "display: inline-block",htmlOutput("widgetPieChartTaxaNum")),
                   tags$div( style = "display: inline-block",htmlOutput("widgetPieChartTaxaMass")),
                   fluidRow(
                     column(6,tableOutput("infoClickedPoint")),  
                     column(6,tableOutput("infoClickedPointTaxa")
                     )
                   ),
                   
                   # Infos zu allen gezeiten Samples
                   h3("Information on all shown samples"),
                   dataTableOutput("statShownDatasets"),
                   plotOutput("histogramDepth", height = 200),
                   plotOutput("histogramPop", height = 200),
                   
                   # Filterkonfiguration
                   h3("Filter configuration"),
                   tags$p(),
                   tableOutput("filterConfig")
                 )
               ),
               
               # Footer
               tags$hr(),
               tags$div(
                 style = "text-align: center",
                 HTML("Copyright &#169; 2017"),
                 tags$a("Alfred Wegener Institute (AWI) | Functional Ecology ", href = "http://www.awi.de/en/science/biosciences/functional-ecology/main-research-focus/ecosystem-functions.html"),
                 " - ",
                 tags$a("Critter", href = "https://github.com/janhoo/critter"),
                 " - Ansprechpartner: ",
                 tags$a("Jan Holstein", href = "mailto:jan.holstein@awi.de"),
                 ",",
                 tags$a("Paul Kloss", href = "mailto:paul.kloss@awi.de"),
                 tags$p()  
               )
        )

# ______________________________________________________
# Starte Shiny
# ______________________________________________________

print("* Starte Shiny-Framework")
print("...")

shinyApp(ui = ui, server = server)
