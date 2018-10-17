var map, toolbar, clippingGeometry;

window.onload = function()
{
    require([
        "esri/map", "esri/toolbars/draw",
        "esri/graphic", "esri/geometry/webMercatorUtils",
        "esri/symbols/SimpleLineSymbol", "esri/symbols/SimpleFillSymbol",
        "dojo/_base/Color", "dojo/dom", "dojo/on", "dojo/domReady!"
    ], function(
        Map, Draw,
        Graphic, webMercatorUtils,
        SimpleLineSymbol, SimpleFillSymbol,
        Color, dom, on
    )
    {
        map = new Map("mapDiv",
        {
            basemap: "ENTER IN THE BASEMAP HERE", //Select the basemap
            center: [,], //Enter the coordinates to center the map
            zoom: , //Set the default zoom
            minZoom: ,//Set the minimum zoom level 
            smartNavigation: false
        });

        map.on("load", function()
        {
            toolbar = new Draw(map);

            dojo.connect(toolbar, "onDrawEnd", addToMap);

            on(dom.byId("draw"), "click", drawPolygon);
            on(dom.byId("reset"), "click", drawReset);
        });

        function addToMap(geometry)
        {
            var symbol = new SimpleFillSymbol(
                SimpleFillSymbol.STYLE_SOLID,
                new SimpleLineSymbol(
                    SimpleLineSymbol.STYLE_DASHDOT,
                    new Color([255, 0, 0]), 2
                ),
                new Color([255, 255, 0, 0.25])
            );
            geometry = webMercatorUtils.webMercatorToGeographic(geometry);
            var graphic = new Graphic(geometry, symbol);
            map.graphics.clear();
            map.graphics.add(graphic);
            toolbar.deactivate(Draw.POLYGON);
            clippingGeometry = geometry.rings[0];
        }

        function drawPolygon()
        {
            drawReset();
            toolbar.activate(esri.toolbars.Draw.POLYGON);
        }

        function drawReset()
        {
            toolbar.deactivate(esri.toolbars.Draw.POLYGON);
            map.graphics.clear();
        }
    });

    FMEServer.init(
    {
        server: "https://demos-safe-software.fmecloud.com", //Update to your FME Server hostname - on FME training machines this is http://fmetraining
        token: "568c604bc1f235bbe137c514e7c61a8436043070" //Update to your fmetoken
    });
};

/*function showResults(json)
{
    // The following is to write out the full return object
    // for visualization of the example
    var hr = document.createElement("hr");
    var div = document.createElement("div");

    // This extracts the download link to the clipped data
    var download = json.serviceResponse.url;


    div.innerHTML += "<hr><a href=\"" + download + "\">Download Result</a>";
    document.body.appendChild(hr);
    document.body.appendChild(div);
}
*/
/*
function processClip()
{
    var repository = ""; //Enter repository name
    var workspace = ""; //Enter the workspace name

    // Process the clippingGeometry into a WKT Polygon string
    var geometry = "POLYGON((";

    for (var i = 0; i < clippingGeometry.length; i++)
    {
        var lat = clippingGeometry[i][1];
        var lng = clippingGeometry[i][0];
        geometry += lng + " " + lat + ",";
    }

    // Remove trailing , from string
    geometry = geometry.substr(0, geometry.length - 1);
    geometry += "))";

    var params = "GEOM=" + geometry;

    // Use the FME Server Data Download Service
    FMEServer.runDataDownload(repository, workspace, params, showResults);
}*/
