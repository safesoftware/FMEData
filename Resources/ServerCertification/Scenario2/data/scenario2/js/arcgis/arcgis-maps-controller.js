// 
//  maps-controller.js
//  demos
//  
//  Created by SHarper on 2012-01-12.
// 
function ArcGisMapsManager() {
  
  this.arcgisMap = new esri.Map("map_canvas", {
		extent : new esri.geometry.Extent(-123.6, 49.11, -122.5, 49.4, new esri.SpatialReference(4326)),
    sliderStyle:"small",
    sliderOrientation:"vertical",
    sliderPosition: "bottom-right"
	});
	var symbol = new esri.symbol.SimpleFillSymbol(esri.symbol.SimpleFillSymbol.STYLE_SOLID, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_DASHDOT, new dojo.Color([255, 0, 0]), 2), new dojo.Color([255, 255, 0, 0.25]));
	this.toolbar = new esri.toolbars.Draw(this.arcgisMap);
		
	var me = this;
	this._addToMap = function(geometry) {
		me.addToMap(geometry)
	};
	
	dojo.connect(this.toolbar, "onDrawEnd", this._addToMap);
  var tiled = new esri.layers.ArcGISTiledMapServiceLayer("http://server.arcgisonline.com/ArcGIS/rest/services/ESRI_StreetMap_World_2D/MapServer");
	this.arcgisMap.addLayer(tiled);
}

/**
 * Add a geometry to map, handles different geometry types
 * @param {Object} geometry
 */
ArcGisMapsManager.prototype.addToMap = function(geometry) {
	switch (geometry.type) {
		case "point":
			var symbol = new esri.symbol.SimpleMarkerSymbol(esri.symbol.SimpleMarkerSymbol.STYLE_SQUARE, 10, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_SOLID, new dojo.Color([255, 0, 0]), 1), new dojo.Color([0, 255, 0, 0.25]));
			break;
		case "polyline":
			var symbol = new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_DASH, new dojo.Color([255, 0, 0]), 1);
			break;
		case "polygon":
			var symbol = new esri.symbol.SimpleFillSymbol(esri.symbol.SimpleFillSymbol.STYLE_SOLID, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_DASHDOT, new dojo.Color([255, 0, 0]), 2), new dojo.Color([255, 255, 0, 0.25]));
			break;
		case "extent":
			var symbol = new esri.symbol.SimpleFillSymbol(esri.symbol.SimpleFillSymbol.STYLE_SOLID, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_DASHDOT, new dojo.Color([255, 0, 0]), 2), new dojo.Color([255, 255, 0, 0.25]));
			break;
		case "multipoint":
			var symbol = new esri.symbol.SimpleMarkerSymbol(esri.symbol.SimpleMarkerSymbol.STYLE_DIAMOND, 20, new esri.symbol.SimpleLineSymbol(esri.symbol.SimpleLineSymbol.STYLE_SOLID, new dojo.Color([0, 0, 0]), 1), new dojo.Color([255, 255, 0, 0.5]));
			break;
	}

	var graphic = new esri.Graphic(geometry, symbol);
	this.arcgisMap.graphics.clear();
	this.arcgisMap.graphics.add(graphic);
	this.toolbar.deactivate(esri.toolbars.Draw.POLYGON);
	var geom = this.getPolygonCoordsText(geometry.rings[0]);
	$('#geom').attr('value', geom);
	$('#geom').change();
}

/**
 * Builds up the OGCWellKnownText string which will be passed into the post request and used by FME Server to generate the
 * bounding box.
 */
ArcGisMapsManager.prototype.getPolygonCoordsText = function(coords) {
	textString = 'POLYGON((';

	// loop to print coords
	for(var i = 0; i < (coords.length); i++) {
		var lat = coords[i][1];
		var longi = coords[i][0];
		textString += longi + ' ';
		textString += lat + ',';
	}

	textString = textString.substring(0,textString.length - 1);
	textString += '))';

	return textString;
}