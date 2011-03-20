var use_dynamic_loc = true;
			var currentLocation = {lat: 41.835877950000004, lng: -87.62874322666666};

			function getCurrentLocation() {
				var location;
				if (use_dynamic_loc==true && navigator.geolocation) {
					navigator.geolocation.getCurrentPosition(function(position) {
						console.log('Your lat-long is: ' + position.coords.latitude + ' / ' + position.coords.longitude);
						console.log('You live in  ' + position.address.city + ', ' + position.address.state)
						location = {
							lat: position.coords.latitude,
							lng: position.coords.longitude
						};
					});
				}
				else {
					location = {
						lat: 41.835820,
						lng:-87.624553
					};
				}
				return location;
			}

			function initializeLocation() {
				var mapLoc = new google.maps.LatLng(currentLocation["lat"], currentLocation["lng"]);
				var geocoder = new google.maps.Geocoder();
				var mapOptions = {
						zoom: 18,
						center: mapLoc,
						mapTypeControlOptions: {
							style: google.maps.MapTypeControlStyle.DROPDOWN_MENU },
						navigationControl: true,
						navigationControlOptions: {
							style: google.maps.NavigationControlStyle.SMALL,
							position: google.maps.ControlPosition.LEFT },
						mapTypeId: google.maps.MapTypeId.HYBRID
					}
	            var map = new google.maps.Map(document.getElementById("map_location"), mapOptions);
				var image = new google.maps.MarkerImage('http://localhost:8000/site_media/images/hot.png',
				      new google.maps.Size(20, 32),
				      new google.maps.Point(0,0),
			 	      new google.maps.Point(0, 32));
				var marker = new google.maps.Marker({
											position: mapLoc,
											map: map,
											draggable: true,
											icon: image
										});
				$('#location_id')[0].value = marker.getPosition().lat() + "," + marker.getPosition().lng();
				google.maps.event.addListener(marker, "dragend", function() {
					var point = marker.getPosition();
					map.panTo(new google.maps.LatLng(point.lat(),point.lng()));
					if (geocoder) {
						geocoder.geocode( {'latLng': point}, function(results, status) {
				 			if (status == google.maps.GeocoderStatus.OK) {
								if (results[1])
									$('#location_id')[0].value = results[1].formatted_address;
							}
							else{
								alert("Geocode was not successful for the following reason: " + status);
							}
						});
					}
				});
			}
			$(document).ready(function (){
				initializeLocation();
			});
		    $(document).unload(function () {GUnload()});
