# -*- coding: utf-8 -*-

from django.forms import MultiValueField, CharField, Field
from form_engine.customWidgets import LocationWidget

class LocationField(Field):
	widget = LocationWidget

	def clean(self, value):
		a, b = value.split(',')
		lat, lng = float(a), float(b)
		return (lat, lng)

class TimeSelectField(MultiValueField):
	"""
	Time multi field. Returns datetime.time object. Must be used together with TimeWidget
	"""
	def __init__(self, *args, **kwargs):
		fields = (
		forms.CharField(),
		forms.CharField()
		)
		super(TimeSelectField, self).__init__(fields, *args, **kwargs)

	def compress(self, data_list):
		if data_list:
			return time(hour=int(data_list[0]), minute=int(data_list[1]))
			return None

class NameField(MultiValueField):
	"""
	Time multi field. Returns datetime.time object. Must be used together with TimeWidget
	"""
	def __init__(self, *args, **kwargs):
		fields = (
		forms.CharField(),
		forms.CharField()
		)
		super(NameField, self).__init__(fields, *args, **kwargs)
		
	def compress(self, data_list):
		if data_list:
			first_name, middle_initial, last_name = data_list[0], data_list[1], data_list[2]
			return [first_name, middle_initial, last_name]
		return None