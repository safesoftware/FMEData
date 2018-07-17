function ArcGISPolygonDrawTools(myArcGISMap){
	this.arcgisMap = myArcGISMap;
}

/**
 * Fired when the user clicks the draw polygon button
 */
ArcGISPolygonDrawTools.prototype.drawPolygon = function() {
	this.clearPolygon();
	this.arcgisMap.toolbar.activate(esri.toolbars.Draw.POLYGON);
}
/**
 * Called when the user clicks the Clear button
 */
ArcGISPolygonDrawTools.prototype.clearPolygon = function() {

	this.arcgisMap.toolbar.deactivate(esri.toolbars.Draw.POLYGON);
	this.arcgisMap.arcgisMap.graphics.clear();
	document.getElementById('geom').value = "";
	dataDist.updateQuery();
}
