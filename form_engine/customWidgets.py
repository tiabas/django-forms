# -*- coding: utf-8 -*-
import re
from django.utils.encoding import force_unicode
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.forms.util import flatatt
from django.forms.widgets import Widget, MultiWidget, RadioInput, Textarea, Select, DateInput, DateTimeInput,\
	RadioFieldRenderer, SelectMultiple, TextInput, TimeInput,\
	CheckboxInput, CheckboxSelectMultiple, HiddenInput
from django.forms.extras.widgets import SelectDateWidget
from django.utils.encoding import StrAndUnicode, force_unicode
from itertools import chain
from django.conf import settings
from django.utils.safestring import mark_safe
import settings

class HTML5EmailInput(TextInput):
    input_type = 'email'

class HTML5NumberInput(TextInput):
    input_type = 'number'

class HTML5TelephoneInput(TextInput):
    input_type = 'tel'

class HTML5DateInput(DateInput):
    input_type = 'date'

class HTML5DateTimeInput(DateTimeInput):
    input_type = 'datetime'

class HTML5TimeInput(TimeInput):
    input_type = 'time'

__all__ = ('SelectTimeWidget', 'SplitSelectDateTimeWidget')

# Attempt to match many time formats:
# Example: "12:34:56 P.M."  matches:
# ('12', '34', ':56', '56', 'P.M.', 'P', '.', 'M', '.')
# ('12', '34', ':56', '56', 'P.M.')
# Note that the colon ":" before seconds is optional, but only if seconds are omitted
time_pattern = r'(\d\d?):(\d\d)(:(\d\d))? *([aApP]\.?[mM]\.?)?$'

RE_TIME = re.compile(time_pattern)
# The following are just more readable ways to access re.matched groups:
HOURS = 0
MINUTES = 1
SECONDS = 3
MERIDIEM = 4

class SelectTimeWidget(Widget):
	"""
		 A Widget that splits time input into <select> elements.
		 Allows form to show as 24hr: <hour>:<minute>:<second>, (default)
		 or as 12hr: <hour>:<minute>:<second> <am|pm>

		 Also allows user-defined increments for minutes/seconds
		 """
	hour_field = '%s_hour'
	minute_field = '%s_minute'
	second_field = '%s_second'
	meridiem_field = '%s_meridiem'
	twelve_hr = False # Default to 24hr.

	def __init__(self, attrs=None, hour_step=None, minute_step=None, second_step=None, twelve_hr=False):
		"""
				  hour_step, minute_step, second_step are optional step values for
				  for the range of values for the associated select element
				  twelve_hr: If True, forces the output to be in 12-hr format (rather than 24-hr)
				  """
		self.attrs = attrs or {}

		if twelve_hr:
			self.twelve_hr = True # Do 12hr (rather than 24hr)
			self.meridiem_val = 'a.m.' # Default to Morning (A.M.)

		if hour_step and twelve_hr:
			self.hours = range(1, 13, hour_step)
		elif hour_step: # 24hr, with stepping.
			self.hours = range(0, 24, hour_step)
		elif twelve_hr: # 12hr, no stepping
			self.hours = range(1, 13)
		else: # 24hr, no stepping
			self.hours = range(0, 24)

		if minute_step:
			self.minutes = range(0, 60, minute_step)
		else:
			self.minutes = range(0, 60)

		if second_step:
			self.seconds = range(0, 60, second_step)
		else:
			self.seconds = range(0, 60)

	def render(self, name, value, attrs=None):
		try: # try to get time values from a datetime.time object (value)
			hour_val, minute_val, second_val = value.hour, value.minute, value.second
			if self.twelve_hr:
				if hour_val >= 12:
					self.meridiem_val = 'p.m.'
				else:
					self.meridiem_val = 'a.m.'
		except AttributeError:
			hour_val = minute_val = second_val = 0
			if isinstance(value, basestring):
				match = RE_TIME.match(value)
				if match:
					time_groups = match.groups();
					hour_val = int(time_groups[HOURS]) % 24 # force to range(0-24)
					minute_val = int(time_groups[MINUTES])
					if time_groups[SECONDS] is None:
						second_val = 0
					else:
						second_val = int(time_groups[SECONDS])

					# check to see if meridiem was passed in
					if time_groups[MERIDIEM] is not None:
						self.meridiem_val = time_groups[MERIDIEM]
					else: # otherwise, set the meridiem based on the time
						if self.twelve_hr:
							if hour_val >= 12:
								self.meridiem_val = 'p.m.'
							else:
								self.meridiem_val = 'a.m.'
						else:
							self.meridiem_val = None


						# If we're doing a 12-hr clock, there will be a meridiem value, so make sure the
						# hours get printed correctly
		if self.twelve_hr and self.meridiem_val:
			if self.meridiem_val.lower().startswith('p') and hour_val > 12 and hour_val < 24:
				hour_val = hour_val % 12
		elif hour_val == 0:
			hour_val = 12

		output = []
		if 'id' in self.attrs:
			id_ = self.attrs['id']
		else:
			id_ = 'id_%s' % name

		# For times to get displayed correctly, the values MUST be converted to unicode
		# When Select builds a list of options, it checks against Unicode values
		hour_val = u"%.2d" % hour_val
		minute_val = u"%.2d" % minute_val
		second_val = u"%.2d" % second_val

		hour_choices = [("%.2d" % i, "%.2d" % i) for i in self.hours]
		local_attrs = self.build_attrs(id=self.hour_field % id_)
		select_html = Select(choices=hour_choices).render(self.hour_field % name, hour_val, local_attrs)
		output.append(select_html)

		minute_choices = [("%.2d" % i, "%.2d" % i) for i in self.minutes]
		local_attrs['id'] = self.minute_field % id_
		select_html = Select(choices=minute_choices).render(self.minute_field % name, minute_val, local_attrs)
		output.append(select_html)

		second_choices = [("%.2d" % i, "%.2d" % i) for i in self.seconds]
		local_attrs['id'] = self.second_field % id_
		select_html = Select(choices=second_choices).render(self.second_field % name, second_val, local_attrs)
		output.append(select_html)

		if self.twelve_hr:
		#  If we were given an initial value, make sure the correct meridiem gets selected.
			if self.meridiem_val is not None and  self.meridiem_val.startswith('p'):
				meridiem_choices = [('p.m.', 'p.m.'), ('a.m.', 'a.m.')]
			else:
				meridiem_choices = [('a.m.', 'a.m.'), ('p.m.', 'p.m.')]

			local_attrs['id'] = local_attrs['id'] = self.meridiem_field % id_
			select_html = Select(choices=meridiem_choices).render(self.meridiem_field % name, self.meridiem_val,
			                                                      local_attrs)
			output.append(select_html)

		return mark_safe(u' '.join(output))

	def id_for_label(self, id_):
		return '%s_hour' % id_
		id_for_label = classmethod(id_for_label)

	def value_from_datadict(self, data, files, name):
	# if there's not h:m:s data, assume zero:
		h = data.get(self.hour_field % name, 0) # hour
		m = data.get(self.minute_field % name, 0) # minute
		s = data.get(self.second_field % name, 0) # second

		meridiem = data.get(self.meridiem_field % name, None)

		#NOTE: if meridiem is None, assume 24-hr
		if meridiem is not None:
			if meridiem.lower().startswith('p') and int(h) != 12:
				h = (int(h) + 12) % 24
			elif meridiem.lower().startswith('a') and int(h) == 12:
				h = 0

		if (int(h) == 0 or h) and m and s:
			return '%s<span>:</span>%s<span>:</span>%s' % (h, m, s)

		return data.get(name, None)

class LikertRadioRenderer(RadioFieldRenderer):
	def render(self):
		"""Outputs a <td> for this set of radio fields."""
		return mark_safe(u'\n'.join([u'<td class="qcol">%s</td>'
		                             % force_unicode(w) for w in self]))

	def __iter__(self):
		for i, choice in enumerate(self.choices):
			yield RadioInput(self.name, self.value, self.attrs.copy(), choice, i)

class PlainText(Widget):
	def __init__(self, attrs=None, *args, **kwargs):
		super(PlainText, self).__init__(attrs)

	def render(self, name=None, value=None, attrs=None):
		if attrs:
			final_attrs = self.build_attrs(attrs)
		return mark_safe(u'<span%s>%s</span>' % (flatatt(final_attrs),
		                                         conditional_escape(force_unicode(value))))

class TimeInputWidget(MultiWidget):
	"""
		 Time Input Widget, see TimeSelectField for info.
		 """

	def __init__(self, *args, **kwargs):
		widgets = (
				TextInput(),
				TextInput(),
				Select(choices=(('am', 'AM'), ('pm', 'PM')))
				)
		super(TimeInputWidget, self).__init__(widgets, *args, **kwargs)

	def decompress(self, value):
		if value:
			return [str(value.hour), str(value.minute), str(value.meridiem)]
		return [None, None, None]

	def format_output(self, rendered_widgets):
		return '<span class="datetime">%s</span>' % u' <span class="colon">:</span> '.join(rendered_widgets)

class SplitSelectDateTimeWidget(MultiWidget):
	"""
		 MultiWidget = A widget that is composed of multiple widgets.

		 This class combines SelectTimeWidget and SelectDateWidget so we have something
		 like SpliteDateTimeWidget (in django.forms.widgets), but with Select elements.
		 """

	def __init__(self, attrs=None, hour_step=None, minute_step=None, second_step=None, twelve_hr=None, years=None):
		""" pass all these parameters to their respective widget constructors..."""
		widgets = (SelectDateWidget(attrs=attrs, years=years),
		           SelectTimeWidget(attrs=attrs,
		                            hour_step=hour_step,
		                            minute_step=minute_step,
		                            second_step=second_step,
		                            twelve_hr=twelve_hr)
		)
		super(SplitSelectDateTimeWidget, self).__init__(widgets, attrs)

	def decompress(self, value):
		if value:
			return [value.date(), value.time().replace(microsecond=0)]
		return [None, None]

	def format_output(self, rendered_widgets):
		"""
				  Given a list of rendered widgets (as strings), it inserts an HTML
				  linebreak between them.
				  Returns a Unicode string representing the HTML for the whole lot.
				  """
		rendered_widgets.insert(-1, '<br/>')
		return u''.join(rendered_widgets)

class NameInputWidget(MultiWidget):
	"""
		 Time Input Widget, see TimeSelectField for info.
		 """

	def __init__(self, middle=True, *args, **kwargs):
		if middle:
			widgets = (
			forms.TextInput(),
			forms.TextInput(),
			forms.TextInput()
			)
		else:
			widgets = (
			forms.TextInput(),
			forms.TextInput()
			)
		super(NameInputWidget, self).__init__(widgets, *args, **kwargs)

		def decompress(self, value):
			if value and middle:
				return [str(value.first_name), str(value.middle_initial), str(value.last_name)]
			elif value and not middle:
				return [str(value.first_name), str(value.last_name)]
			return [None, None, None]

		def format_output(self, rendered_widgets):
			return '<span class="name">%s</span>' % u' '.join(rendered_widgets)

class CustomCheckboxSelectMultiple(SelectMultiple):
	def render(self, name, value, attrs=None, choices=()):
		if value is None: value = []
		has_id = attrs and 'id' in attrs
		final_attrs = self.build_attrs(attrs, name=name)
		output = [u'']
		# Normalize to strings
		str_values = set([force_unicode(v) for v in value])
		for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
		# If an ID attribute was given, add a numeric index as a suffix,
		# so that the checkboxes don't all have the same ID attribute.
			if has_id:
				final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
				label_for = u' for="%s"' % final_attrs['id']
			else:
				label_for = ''

			cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
			option_value = force_unicode(option_value)
			rendered_cb = cb.render(name, option_value)
			option_label = conditional_escape(force_unicode(option_label))
			output.append(u'<span><label%s>%s %s</label></span>' % (label_for, rendered_cb, option_label))
		return mark_safe(u'\n'.join(output))


class CheckboxSelectMultipleAsTable(CheckboxSelectMultiple):
	items_per_row = 4 # Number of items per row

	def render(self, name, value, attrs=None, choices=()):
		if value is None: value = []
		has_id = attrs and 'id' in attrs
		final_attrs = self.build_attrs(attrs, name=name)
		output = ['<table><tr>']
		# Normalize to strings
		str_values = set([force_unicode(v) for v in value])
		for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
		# If an ID attribute was given, add a numeric index as a suffix,
		# so that the checkboxes don't all have the same ID attribute.
			if has_id:
				final_attrs = dict(final_attrs, id='%s_%s' % (attrs['id'], i))
				label_for = ' for="%s"' % final_attrs['id']
			else:
				label_for = ''
			cb = forms.CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
			option_value = force_unicode(option_value)
			rendered_cb = cb.render(name, option_value)
			option_label = conditional_escape(force_unicode(option_label))
			if i != 0 and i % self.items_per_row == 0:
				output.append('</tr><tr>')
			output.append('<td nowrap><label%s>%s %s</label></td>' % (label_for, rendered_cb, option_label))
		output.append('</tr></table>')
		return mark_safe('\n'.join(output))

class LocationWidget(Widget):
	DEFAULT_WIDTH = 500
	DEFAULT_HEIGHT = 300

	def __init__(self, *args, **kwargs):
		self.dynamic_loc = "true"
		if kwargs.has_key("dynamic_loc"):
			self.dynamic_loc = kwargs.pop("dynamic_loc", "true")
		self.map_width = kwargs.pop("map_width", self.DEFAULT_WIDTH)
		self.map_height = kwargs.pop("map_height", self.DEFAULT_HEIGHT)
		super(LocationWidget, self).__init__(*args, **kwargs)
		self.inner_widget = TextInput(attrs=kwargs.get('attrs'))

	def render(self, name, value, *args, **kwargs):
		if not value:
			value = settings.GEO_LOCATION
		if isinstance(value, unicode):
			a, b = value.split(',')
		else:
			a, b = value.split(',')
		lat, lng = float(a), float(b)

		js = '''
		<script type="text/javascript">
			var $loadingIndicator = $('<img/>').attr({
				'id': 'ajaxloader',
				'src': '/site_media/images/loading.gif',
				'alt': 'Obtaining your location. Please wait.',
				'style': 'border: 1px solid #fff;margin: 0 10px 0 0' })
				.addClass('loader');
			var loading_div = null;
			var use_dynamic_loc = %(useDynamicLocation)s;
			var defaultLocation = {lat: 41.83587795000, lng: -87.62874322666};
			var geo_accuracy = 60;
			
			var geo_options = {
			 timeout: 12000,
			 maximumAge: 6000,
			 enableHighAccuracy: false
			};

			function geoSuccess(position) {
			}

			function geoError(error) {
				switch(error.code)
				{
					 case error.PERMISSION_DENIED: 
						alert("user did not share geolocation data");
						break;
					 case error.POSITION_UNAVAILABLE: 
						alert("could not detect current position");
					 	break;
					 case error.TIMEOUT: 
						// alert("retrieving position timed out");
						$('#loading').html("geolocation failed! using default location", function() {});
						initializeLocation(defaultLocation);
						$('#loading').slideUp('slow', function() {
							$('#map_%(name)s').slideDown('slow');
						});
						break;
					 default: 
						alert("unknown error");
						break;
				}
			}

			function getCurrentLocation() {
				var location;
				if (use_dynamic_loc==true && navigator.geolocation) {
					console.log('loading');
					$('#loading').html($loadingIndicator); 
					//$('#loading').slideDown('slow', function() { 
					$('<span id="feedback">Obtaining GPS co-ordinates...</span>').insertAfter('#ajaxloader');
					//});
					
					navigator.geolocation.getCurrentPosition(function(position) {
						//console.log('Your lat-long is: ' + position.coords.latitude + ' / ' + position.coords.longitude);
						//console.log('You live in  '+position.address.city +', '+position.address.streetNumber+', '+position.address.street);
						console.log('Accuracy: ' + position.coords.accuracy);
						console.log('Altitude Accuracy: ' + position.coords.altitudeAccuracy);
						geo_accuracy = position.coords.accuracy;
						location = {
							lat: position.coords.latitude,
							lng: position.coords.longitude
						};
						$('#feedback').html('Loading map...');
						
						initializeLocation(location);
						
						$('#loading').slideUp('slow', function() {
							$('#map_%(name)s').slideDown('slow');
						});
					}, geoError, geo_options);
				}
				else { alert('error not location api'); }
			}

			function handle_errors(error) {
				switch(error.code)
				{
					 case error.PERMISSION_DENIED: alert("user did not share geolocation data");
					 break;

					 case error.POSITION_UNAVAILABLE: alert("could not detect current position");
					 break;

					 case error.TIMEOUT: alert("retrieving position timed out");
					 break;

					 default: alert("unknown error");
					 break;
				}
			}

			function initializeLocation(currLoc) {
				var currentLocation = currLoc;
				var mapLoc = new google.maps.LatLng(currentLocation["lat"], currentLocation["lng"]);
				var geocoder = new google.maps.Geocoder();
				var mapOptions = {
						zoom: 17,
						center: mapLoc,
						mapTypeControlOptions: {
							style: google.maps.MapTypeControlStyle.DROPDOWN_MENU },
						navigationControl: true,
						navigationControlOptions: {
							style: google.maps.NavigationControlStyle.SMALL,
							position: google.maps.ControlPosition.LEFT },
						mapTypeId: google.maps.MapTypeId.ROADMAP
					};
	            var map = new google.maps.Map(document.getElementById("map_%(name)s"), mapOptions);
				
				var image = new google.maps.MarkerImage('/site_media/images/farallon.png',
							new google.maps.Size(16, 16),
							new google.maps.Point(0,0),
							new google.maps.Point(8,8));	
										
				var marker = new google.maps.Marker({
									position: mapLoc, 
									map: map, 
									draggable: true,
									icon: image,
								});

				var draw_circle = new google.maps.Circle({
									center: marker.position,
									radius: geo_accuracy,
									strokeColor: "#1CA8F9",
									strokeOpacity: 0.8,
									strokeWeight: 2,
									fillColor: "#888888",
									fillOpacity: 0.35,
									map: map
								});
				draw_circle.bindTo('center', marker, 'position');
				$('#%(name)s_id')[0].value = marker.getPosition().lat() + "," + marker.getPosition().lng();

				google.maps.event.addListener(marker, "dragend", function() {
					var point = marker.getPosition();
					map.panTo(new google.maps.LatLng(point.lat(),point.lng()));
					if (geocoder) {
						geocoder.geocode( {'latLng': point}, function(results, status) {
				 			if (status == google.maps.GeocoderStatus.OK) {
								if (results[1])
									$('#%(name)s_id')[0].value = results[1].formatted_address;
							}
							else{
								alert("Geocode was not successful for the following reason: " + status);
							}
						});
					}
				});
			}

			$(document).ready(function (){
				getCurrentLocation();
			});
			
		    $(document).unload(function () {GUnload()});

		</script>
		''' % dict(name=name, lat=lat, lng=lng, useDynamicLocation=self.dynamic_loc)
		html = self.inner_widget.render("%s" % name, None, dict(id='%s_id' % name))
		html += """
				<div id="loading" style="border: 1px solid #FFF;margin: 10px 0; padding: 5px 0 5px 0px;"></div>
				<div id=\"map_%s\" class=\"gmap\" style=\"width: %dpx; height: %dpx;\">
				</div>
				""" % (name, self.map_width, self.map_height)
		return mark_safe(js + html)

	# class TinyMCEEditor(Textarea):
	#
	# 	def render(self, name, value, attrs=None):
	# 		rendered = super(TinyMCEEditor, self).render(name, value, attrs)
	# 		return rendered + mark_safe(u'''<script type="text/javascript">
	# 		jQuery('#id_%s').tinymce({
	# 		script_url : '%sjs/tiny_mce/tiny_mce.js',
	# 		mode : "textareas",
	# 		convert_urls : false,
	# 		width:  200,
	# 		height: 200,
	# 		theme : "advanced",
	# 		plugins : "table,searchreplace",
	# 		theme_advanced_buttons1 : "bold,italic,underline,separator,link,unlink,image,strikethrough,separator,bullist,
	# 		numlist,separator,indent,outdent,separator,justifyleft,justifycenter,justifyright,justifyfull,separator,undo,redo,
	# 		separator,formatselect,separator,search,replace,separator,code",
	# 		theme_advanced_buttons2 : "tablecontrols",
	# 		theme_advanced_buttons3 : "",
	# 		theme_advanced_toolbar_location : "top",
	# 		theme_advanced_toolbar_align : "left",
	# 		theme_advanced_path_location : "bottom",
	# 		extended_valid_elements : "a[name|href|target|title|onclick]"
	# 		});
	# 		</script>''' % (name, settings.MEDIA_URL))
