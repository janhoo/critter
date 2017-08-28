
library(shiny)
library(rgdal)
library(raster)
r <- raster(system.file("external/test.grd", package="raster"))
# take a small part
r <- crop(r, extent(179880, 180800, 329880, 330840) )



# Define server logic 
shinyServer(function(input, output) {

  output$main.map <- renderPlot({
    plot(r,col=rev(heat.colors(200)))
  })
  
  # Generate a summary of the data
  output$summary <- renderPrint({
    summary(r)
  })

  
  output$downloadData <- downloadHandler(
    filename = function() { paste('testraster','.tif', sep='') },
    content = function(file) {
      writeRaster(r,filename=file,format="GTiff")
    },
    contentType = "image/gif"
  )

  
  output$downloadSummary <- downloadHandler(
    filename = function() { paste('testraster','.csv', sep='') },
    content = function(file) {
      write.csv(summary(r), file)
    },
    contentType = "text/csv"
  )
  
  
})