function GoogleMapsManager() {
	//Initialise Google Maps
	//
	var me = this;
	var mapOptions = {
		center: new google.maps.LatLng(lat, lon),
		zoom: 12,
		disableDefaultUI: true,
		zoomControl: true,
		panControl: true,
		drawingControl: true,
		drawingControlOptions: {
			position: google.maps.ControlPosition.TOP_RIGHT,
			drawingModes: [
				google.maps.drawing.OverlayType.POLYGON
			]
		},
		zoomControlOptions: {
			position: google.maps.ControlPosition.RIGHT_CENTER,
			style: google.maps.ZoomControlStyle.SMALL
		},
		panControlOptions: {
			position: google.maps.ControlPosition.RIGHT_CENTER
		}
	}

	me.myGoogleMap = new google.maps.Map(document.getElementById('map_canvas'), mapOptions);

};

