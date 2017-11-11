/**
 * @fileoverview Runs the Ecodash Tool application. The code is executed in the
 * user's browser. It communicates with the App Engine backend, renders output
 * to the screen, and handles user interactions.
 */

// define a number of global variabiles
var DataArr = [];
var all_overlays = [];
var map;
var currentShape;


 /**
 * Starts the Surface Water Tool application. The main entry point for the app.
 * @param {string} eeMapId The Earth Engine map ID.
 * @param {string} eeToken The Earth Engine map token.
 */
var boot = function(eeMapId, eeToken) {

	google.load('visualization', '1.0');

	var app = new App(eeMapId,
					  eeToken
					  );
};



// ---------------------------------------------------------------------------------- //
// The application
// ---------------------------------------------------------------------------------- //
/**
 * The main Surface Water Tool application.
 * @param {google.maps.ImageMapType} mapType The map type to render on the map.
 */
var App = function(eeMapId, eeToken) {

  // Create and display the map.
  map = createMap();

  // Load the default image.
  refreshImage(eeMapId, eeToken);


  channel = new goog.appengine.Channel(eeToken);

  // create listeners for buttons and sliders
  setupListeners();

	$(function () {
	  $("#datepicker").datepicker({
	        autoclose: true,
	        todayHighlight: true
	  }).datepicker('update', new Date('01-01-2000'));
	});

	$(function () {
	  $("#datepicker2").datepicker({
	        autoclose: true,
	        todayHighlight: true
	  }).datepicker('update', new Date('12-31-2000'));
	});

  // run the slider function to initialize the dates
  slider();

 };

/**
 * Creates a Google Map for the given map type rendered.
 * The map is anchored to the DOM element with the CSS class 'map'.
 * @param {google.maps.ImageMapType} mapType The map type to include on the map.
 * @return {google.maps.Map} A map instance with the map type rendered.
 */
var createMap = function() {

  // set the map options
  var mapOptions = {
    center: DEFAULT_CENTER,
    zoom: DEFAULT_ZOOM,
	maxZoom: MAX_ZOOM,
	streetViewControl: false,
	mapTypeId: 'satellite'
  };

  var map = new google.maps.Map(document.getElementById('map'), mapOptions);

	var layer = new google.maps.FusionTablesLayer({
    query: {
      from: '1FOW0_lYQNG3ku2ffNyoORbzDXglPvfMyXmZRb8dj'
    },
    styles: [{
      polygonOptions: {
        fillColor: '#FFFFFF',
        fillOpacity: 0.01,
				strokeColor: "#FFFFFF",
    		strokeWeight: 3
      }
    }]
	});
	layer.setMap(map);

  return map;
};


/**
* setup the event listeners for the buttons and sliders
**/
function setupListeners() {

  document.getElementById('updateMap').addEventListener("click", updateButton);

  document.getElementById('datepicker').addEventListener("change", slider);
  document.getElementById('datepicker2').addEventListener("change", slider);
  // document.getElementById('opacitySlider').addEventListener("change", opacitySliders);
	$('#opacitySlider').slider().on('slideStop',opacitySliders)

   // kml upload function
  // document.getElementById('files').addEventListener('change', fileOpenDialog, false);

  document.getElementById('polygon-selection-method').addEventListener("click",  polygonSelectionMethod);
	document.getElementById('polygon-clear-method').addEventListener("click",  polygonClearMethod);

  document.getElementById('link').addEventListener("click",  hideLink);
	document.getElementById('chartButton').addEventListener("click",plot);

}

/**
* Display the polygons when the radio button changes
**/
function polygonSelectionMethod(data){

	// clear existing overlays
	clearMap();

	// setup drawing
	createDrawingManager();

}

function plot(){
	showChart(data['timeSeries']);
}

function polygonClearMethod(){
	// clear existing overlays
	clearMap();

	drawingManager.setDrawingMode(null);

	hideLink()
}

/**
* hide the download URL when clicked
**/
function hideLink(){

	$('#link').addClass('disabled').prop('disabled', true);
	$('#chartButton').addClass('disabled').prop('disabled', true);

}

/**
* Clear polygons from the map when changing from country to province
**/
var clearMap = function(){

	// remove all polygons
	map.data.forEach(function (feature) {
		 map.data.remove(feature);});

	for (var i=0; i < all_overlays.length; i++)
	 {
		all_overlays[i].overlay.setMap(null);
	}

	all_overlays = [];

	map.setOptions({draggableCursor:''});

}

/**
* create the drawingmanager
**/
var createDrawingManager = function(){

		drawingManager = new google.maps.drawing.DrawingManager({
		drawingMode: google.maps.drawing.OverlayType.POLYGON,
		drawingControl: false,
		polygonOptions: {
			fillColor: "Black",
			strokeColor: "Black"
		  }
		});

		drawingManager.setMap(map);

		// Respond when a new polygon is drawn.
		google.maps.event.addListener(drawingManager, 'overlaycomplete',

		function(event) {
			clearMap();
			all_overlays.push(event);
			drawingManager.setOptions({
			polygonOptions: {
			fillColor:  "Black",
			strokeColor:  "Black"
			  }
		});

          var geom = event.overlay.getPath().getArray();
          currentShape = new google.maps.Polygon({ paths: geom});
          exportMap();

        });

}

/**
* function to show info screen
* using the info button
 */
var showInfo = function() {

   // get infoscreen by id
   var infoscreen = document.getElementById('general-info');

   // open or close screen
   if  (infoscreen.style.display === 'none') {
	infoscreen.style.display = 'block';
	} else {
      infoscreen.style.display = 'none';
    }
}


/**
* function to close info screen
* using the get started button
 */
var getStarted = function() {

   // get infoscreen by id
   var infoscreen = document.getElementById('general-info');

   // close the screen
   infoscreen.style.display = 'none';
}

/**
* function to collapse menu
**/
function collapseMenu() {

   var menu = document.getElementById('ui');
	 var mapView = document.getElementById('map')
   var settings_button = document.getElementById('settings-button');

	if  (menu.style.display == 'none') {
		 menu.style.display = 'block';
		 mapView.style.width = '70%';
		 settings_button.style.display="none";
	} else {
		menu.style.display = 'none';
		mapView.style.width = '100%';
		settings_button.style.display = 'block';
    }
}

/**
* toggle between the home and about page
* go to the home page
**/
var homePage = function(){
	showmap = document.getElementById('map');
	showmap.style.display = "block";

	showUI = document.getElementById('ui');
	showUI.style.display = "block";

	hideAbout = document.getElementById('about');
	hideAbout.style.display = "hide";

	showLegend = document.getElementById('legend');
	showLegend.style.display = "block";
}

/**
* toggle between the home and about page
* go to the about page
**/
var aboutPage = function(){
	hidemap = document.getElementById('map');
	hidemap.style.display = "none";

	hideUI = document.getElementById('ui');
	hideUI.style.display = "none";

	showAbout = document.getElementById('about');
	showAbout.style.display = "block";

	hideLegend = document.getElementById('legend');
	hideLegend.style.display = "none";
}

/**
* hide the update button and show the map
**/
function updateButton() {

	update_button = document.getElementById('updateMap')

	ShowMap();
}



/**
* function to close info screen
* using the get started button
 */
var slider = function() {

	// Without JQuery
	var slider = new Slider('#monthSlider', {});

	// Without JQuery
	var opacSlider = new Slider('#opacitySlider', {});

	// var slider1 = document.getElementById("sliderval1");
  //   slider1.innerHTML = refStart;
	//
	// var slider2 = document.getElementById("sliderval2");
  //   slider2.innerHTML = refStop;

}

/**
* function to close info screen
* using the get started button
 */
var GetDates = function() {

	refStart = $('#datepicker').data('datepicker').getFormattedDate('yyyy-mm-dd');
	refStop = $("#datepicker2").data('datepicker').getFormattedDate('yyyy-mm-dd');

	months = $('#monthSlider').val()

	return [refStart, refStop,months]
}



/**
 * Update map
 */
var ShowMap = function() {

	// clear the map
	map.overlayMapTypes.clear();

	var Dates = GetDates();

	console.log(Dates);

	var params = {};

	// set the parameters
	params['refLow'] = Dates[0]
	params['refHigh'] = Dates[1]
	params['months'] = Dates[2]

	$(".spinner").toggle();

	$.ajax({
      url: "/details",
	  data: params,
      dataType: "json",
      success: function (data) {
		 var mapType = getEeMapType(data.eeMapId, data.eeToken);
		 map.overlayMapTypes.push(mapType);
		 $(".spinner").toggle();

      },
      error: function (data) {
        alert("An error occured! Please refresh the page.");
      }
    });


}




// ---------------------------------------------------------------------------------- //
// Layer management
// ---------------------------------------------------------------------------------- //

/** Updates the image based on the current control panel config. */
var refreshImage = function(eeMapId, eeToken) {
  var mapType = getEeMapType(eeMapId, eeToken);
  map.overlayMapTypes.push(mapType);
};

var opacitySliders = function() {
  setLayerOpacity($("#opacitySlider").val())
}

var setLayerOpacity = function(value) {
  map.overlayMapTypes.forEach((function(mapType, index) {
    if (mapType) {
	  var overlay = map.overlayMapTypes.getAt(index);
      overlay.setOpacity(parseFloat(value));
    }
  }).bind(this));
};

/**
* Function need for kml download function
**/
var setRectanglePolygon = function (newShape) {
    clearPolygon();
    currentShape = newShape;

};


/** Clears the current polygon and cancels any outstanding analysis.
 * * Function need for kml download function
**/
var clearPolygon = function () {
    if (currentShape) {
        currentShape.setMap(null);
        currentShape = undefined;
    }
};


/**
* function to download the map
*/
var exportMap = function() {

	var coords = getCoordinates(currentShape);

	var Dates = GetDates();

	var data = {refLow : Dates[0],
			  refHigh : Dates[1],
			  months: Dates[2]
			  }


	$.get('/downloadHandler?polygon=' + JSON.stringify(coords),data).done((function(data) {
    if (data['error']) {
       alert("An error! This is embarrassing! Please report to the sys admin. ");
    } else {

		var showlink = document.getElementById("link")
		$('#link').removeClass('disabled').prop('disabled', false);
		showlink.setAttribute('href',data)


		$('#chartButton').removeClass('disabled').prop('disabled', false);
    }
	}).bind(this));

}


/**
* Function need for kml function
**/
// Extract an array of coordinates for the given polygon.
var getCoordinates = function (shape) {

    //Check if drawn shape is rectangle or polygon
    if (shape.type == google.maps.drawing.OverlayType.RECTANGLE) {
        var bounds = shape.getBounds();
        var ne = bounds.getNorthEast();
        var sw = bounds.getSouthWest();
        var xmin = sw.lng();
        var ymin = sw.lat();
        var xmax = ne.lng();
        var ymax = ne.lat();


        return [[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]];

    }
    else {
        var points = shape.getPath().getArray();
        return points.map(function (point) {
            return [point.lng(), point.lat()];
        });
    }
};

/**
 * Shows a chart with the given timeseries.
 * @param {Array<Array<number>>} timeseries The timeseries data
 *     to plot in the chart.
 */
 var showChart = function(timeseries) {
  timeseries.forEach(function(point) {
    point[0] = new Date(parseInt(point[0], 10));
  }.bind(this));
  var data = new google.visualization.DataTable();
  data.addColumn('date');
  data.addColumn('number');
  data.addRows(timeseries);
  var wrapper = new google.visualization.ChartWrapper({
    chartType: 'LineChart',
    dataTable: data,
    options: {
      title: 'Total Suspended Solids over time',
      curveType: 'function',
      legend: {position: 'none'},
      titleTextStyle: {fontName: 'Roboto'}
    }
  });
};


// ---------------------------------------------------------------------------------- //
// Static helpers and constants
// ---------------------------------------------------------------------------------- //

function toggleOptions(x) {
    x.classList.toggle("change");

    var options = document.getElementById("ui");
    if (options.style.display === "none") {
        options.style.display = "block";
    } else {
        options.style.display = "none";
    }
		document.getElementById('map').setAttribute("class", "mapChange")
}

/**
 * Generates a Google Maps map type (or layer) for the passed-in EE map id. See:
 * https://developers.google.com/maps/documentation/javascript/maptypes#ImageMapTypes
 * @param {string} eeMapId The Earth Engine map ID.
 * @param {string} eeToken The Earth Engine map token.
 * @return {google.maps.ImageMapType} A Google Maps ImageMapType object for the
 *     EE map with the given ID and token.
 */
var getEeMapType = function(eeMapId, eeToken) {
  var eeMapOptions = {
    getTileUrl: function(tile, zoom) {
      var url = EE_URL + '/map/';
      url += [eeMapId, zoom, tile.x, tile.y].join('/');
      url += '?token=' + eeToken;
      return url;
    },
    tileSize: new google.maps.Size(256, 256),
    name: 'MekongWQ',
	opacity: 1.0,
	mapTypeId: 'satellite'
  };
  return new google.maps.ImageMapType(eeMapOptions);
};

/** @type {string} The Earth Engine API URL. */
var EE_URL = 'https://earthengine.googleapis.com';

/** @type {number} The default zoom level for the map. */
var DEFAULT_ZOOM = 7;

/** @type {number} The max allowed zoom level for the map. */
var MAX_ZOOM = 15;

/** @type {Object} The default center of the map. */
var DEFAULT_CENTER = {lng: 104.043, lat: 15.793};

/** @type {string} The default date format. */
var DATE_FORMAT = 'yyyy-mm-dd';

/** The drawing manager	*/
var drawingManager;
