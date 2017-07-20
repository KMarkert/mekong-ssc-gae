// load this on body load
//document.getElementById('fileOpen').addEventListener('change', fileOpenDialog, false);

function fileOpenDialog(evt ) {
	
	clearMap();
    var files = evt.target.files; // FileList object
    var file = files[0];   
    var reader = new FileReader();

    // Closure to capture the file information.
    reader.onload = (function(theFile) {
        return function (e) {            
            var kmlText = e.target.result;
            var xmlDoc;
            if (window.DOMParser) {
                var parser = new DOMParser();                
                xmlDoc = parser.parseFromString(kmlText, "text/xml");                
            }
            else // Internet Explorer
            {
                xmlDoc = new ActiveXObject("Microsoft.XMLDOM");
                xmlDoc.async = false;
                xmlDoc.loadXML(kmlText);
            }
            //console.log(xmlDoc);

            ////alert(kmlText);
            var v = toGeoJSON.kml(xmlDoc);
            var polyCoords = [];           
            //console.log(v);
           

            var z = v.features[0].geometry.coordinates[0];

            for (var i = 0; i < z.length; i++) {
                polyCoords.push({ lat: z[i][1], lng: z[i][0] })
                //console.log('okok')

            }

            setRectanglePolygon(currentShape);

            currentShape = new google.maps.Polygon({ paths: polyCoords });            
       
          
            currentShape.setMap(map);
            
            exportMap();

            // ADDED by ATE 23 Jan 2017
            // Instantly higlight the polygon and show the title of the polygon.
		    
            //counter = counter + 1;      
            //var title = "uploaded kml"
            //myName.push(title);
            //GEE_call_graph_uploaded_poly(polyCoords);

        };
    })(file);

    // Read in the image file as a data URL.
    reader.readAsText(file);
    //document.getElementById("openedKmlFile").value =file.name;
    
}




//for saving kml

function saveKMLFile() {
   
    var fileName = prompt("Please enter KML filename", "MyPolygon");
    if (fileName != null) {

        if (fileName == "") {
            alert('Please enter the file name for saving!');
            return;
        }
        

        //kmlText = templateKml;
        var kmlText = generateKml(currentShape); //current shape defined in scripts.js

        fileName += '.kml';

        saveTextAsFile(kmlText, fileName);

    }


}

// start taken from http://thiscouldbebetter.neocities.org/texteditor.html
function saveTextAsFile(content, filename) {
    var textToWrite = content;//document.getElementById("inputTextToSave").value;
    var textFileAsBlob = new Blob([textToWrite], { type: 'text/plain' });
    var fileNameToSaveAs = filename;// document.getElementById("inputFileNameToSaveAs").value;

    var downloadLink = document.createElement("a");
    downloadLink.download = fileNameToSaveAs;
    downloadLink.innerHTML = "Download File";
    if (window.webkitURL != null) {
        // Chrome allows the link to be clicked
        // without actually adding it to the DOM.
        downloadLink.href = window.webkitURL.createObjectURL(textFileAsBlob);
    }
    else {
        // Firefox requires the link to be added to the DOM
        // before it can be clicked.
        downloadLink.href = window.URL.createObjectURL(textFileAsBlob);
        downloadLink.onclick = destroyClickedElement;
        downloadLink.style.display = "none";
        document.body.appendChild(downloadLink);
    }

    downloadLink.click();
}

function destroyClickedElement(event) {
    document.body.removeChild(event.target);
}

function loadFileAsText() {
    var fileToLoad = document.getElementById("fileToLoad").files[0];

    var fileReader = new FileReader();
    fileReader.onload = function (fileLoadedEvent) {
        var textFromFileLoaded = fileLoadedEvent.target.result;
        document.getElementById("inputTextToSave").value = textFromFileLoaded;
    };
    fileReader.readAsText(fileToLoad, "UTF-8");
}

// start end

function getGeomKML1() {
    var rGeom = featureSet.features[0].geometry
    var rGeometry = esri.geometry.webMercatorToGeographic(rGeom);
    var x = [];
    var y = [];

    for (var p = 0; p < rGeometry.paths[0].length; p++) {
        x.push(rGeometry.paths[0][p][0]);
        y.push(rGeometry.paths[0][p][1]);
    }

    //for calculating chainage   
    var geom =x[0]+","+y[0]+ ",0";
    for (var i = 1; i < x.length; i++) {
        geom +=" "+ x[i] + "," + y[i] + ",0";
    }

    return geom;
}



// Extract an array of coordinates for the given polygon.
var getGeomKML = function (shape) {

    var geom = '';


    //Check if drawn shape is rectangle or polygon
    if (shape.type == google.maps.drawing.OverlayType.RECTANGLE) {
        var bounds = shape.getBounds();
        var ne = bounds.getNorthEast();
        var sw = bounds.getSouthWest();
        var xmin = sw.lng();
        var ymin = sw.lat();
        var xmax = ne.lng();
        var ymax = ne.lat();

        geom += xmin + ',' + ymin + ',0';
        geom += ' ' + xmax + ',' + ymin + ',0';
        geom += ' ' + xmax + ',' + ymax + ',0';
        geom += ' ' + xmin + ',' + ymax + ',0';
        geom += ' ' + xmin + ',' + ymin + ',0';

        return geom;

    }
    else {
        var points = shape.getPath().getArray();

        geom += points[0].lng() + ',' + points[0].lat() + ',0';

        for (i = 1; i < points.length; i++) {
            geom += ' ' + points[0].lng() + ',' + points[0].lat() + ',0';
        }

        geom += ' ' + points[0].lng() + ',' + points[0].lat() + ',0'
        return geom;
     
    }
};






// Customized from Function BlitzMap - blitz.gmap3.js (http://www.geocodezip.com/blitz-gmap-editor/test5.html)

function generateKml (shape) {
    
    var xw = new XMLWriter('UTF-8');
    xw.formatting = 'indented';//add indentation and newlines
    xw.indentChar = ' ';//indent with spaces
    xw.indentation = 2;//add 2 spaces per level

    xw.writeStartDocument();
    xw.writeStartElement('kml');
    xw.writeAttributeString("xmlns", "http://www.opengis.net/kml/2.2");
    xw.writeStartElement('Document');

        xw.writeStartElement('Placemark');
        xw.writeStartElement('name');
    
        xw.writeCDATA('User defined polygon');
        xw.writeEndElement();
    
       
            xw.writeStartElement('Polygon');
            xw.writeElementString('extrude', '1');
            xw.writeElementString('altitudeMode', 'clampToGround');                       
            xw.writeStartElement('outerBoundaryIs');
            xw.writeStartElement('LinearRing');
            xw.writeStartElement("coordinates");

            var coords = getCoordinates(shape);

            for (var i = 0; i < coords.length; i++) {                
                xw.writeString(coords[i][0] + "," + coords[i][1] + ",0");                
            }
            xw.writeString(coords[0][0] + "," + coords[0][1] + ",0");  
              
            xw.writeEndElement();
            xw.writeEndElement();
            xw.writeEndElement();
                                     
            xw.writeEndElement();

        xw.writeEndElement(); // END PlaceMarker


    xw.writeEndElement();
    xw.writeEndElement(); //End kml
    xw.writeEndDocument();

    var xml = xw.flush(); //generate the xml string
    xw.close();//clean the writer
    xw = undefined;//don't let visitors use it, it's closed
   
    return xml;

}



   



