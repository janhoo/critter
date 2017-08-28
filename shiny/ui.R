library(shiny)
shinyUI(pageWithSidebar(
  
 
  headerPanel("Download Raster Map"),
  
  sidebarPanel(
    downloadButton('downloadData', 'DownloadRaster'),
    br(), br(), br(), br(), br(),
    downloadButton('downloadSummary', 'DownloadText')
    ),
  
  mainPanel(
    
    plotOutput(outputId ="main.map"),
    
    h4("Summary"),
    verbatimTextOutput("summary")
    )
))


