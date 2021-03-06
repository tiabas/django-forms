# -*- coding: utf-8 -*-
from django.conf.urls.defaults import *
from django.utils.functional import lazy
from django.views.generic.simple import direct_to_template
from django.views.generic.simple import redirect_to
from django.contrib import admin

from apps.form_engine.views import *
reverse_lazy = lazy(reverse, unicode)

urlpatterns = patterns('',
	url(r'^forms/$', redirect_to, {'url': '/forms/manage/'}, name='forms'),
	
	url(r'^forms/manage/$',
		view_main_page,
		name='forms_home'),

	url(r'^forms/manage/(?P<form_id>\d+)/restore/$',
		restore_deleted_template,
		name='form_template_restore'),
		
	url(r'^forms/manage/(?P<form_id>\d+)/delete/$',
	    delete_form_template,
	    name='form_template_delete'),

	url(r'^forms/manage/(?P<form_id>\d+)/entries/$',
	    view_template_responses,
	    name='form_template_responses'),
		
	url(r'^forms/manage/(?P<form_id>\d+)/view/?$',
	    preview_form_template,
	    name='form_template_view'),
	
	url(r'^forms/trash/$',
		view_deleted_templates,
		name='my_deleted_templates'),

	url(r'^forms/new/$',
		create_form_template,
		name='form_template_create'),
		
	url(r'^forms/copy/(?P<form_id>\d+)/$',
		copy_form_template,
		name='form_template_copy'),
		
	url(r'^forms/public/view/$',
		view_public_templates,
		name='form_template_public'),
	
	url(r'^forms/public/import/(?P<template_slug>[-\w]+)/$',
		import_form_template,
		name='form_template_import'),

	url(r'^forms/entries/$',
		view_filled_forms,
		name='my_filled_forms'),

	url(r'^forms/entries/success/$',
		submission_success,
		name='form_success_page'),
		
	url(r'^forms/entries/view/(?P<form_uuid>[a-fA-F0-9]{10,40})?/$',
		view_form_entry,
		name='form_entry_view'),
	    
	url(r'^forms/(?P<form_slug>[-\w]+)/view/(?P<form_uuid>[a-fA-F0-9]{10,40})?/?$',
	    process_submission,
	    name='form_send_data'),

	url(r'^forms/design/(?P<form_id>\d+)/save/$',
	    save_form_field,
	    name='save_form_field'),

	url(r'^forms/design/(?P<form_id>\d+)/edit/$',
	    edit_form_template,
	    name='form_template_edit'),
	
	url(r'^forms/design/(?P<form_id>\d+)/settings/$',
	    edit_survey_settings,
	    name='form_settings_update'),
	    
	# url(r'^forms/(?P<form_id>\d+)/edit/fields/$',
	#     question_add,
	#     name='add_field'),

	url(r'^forms/design/(?P<form_id>\d+)/edit/fields/add/(?P<field_type>[-_\w]+)/$',
	    add_field_type,
	    name='add_field_type'),

	url(r'^forms/design/(?P<form_id>\d+)/delete/field/$',
	    question_delete,
	    name='delete_field'),

	url(r'^forms/(?P<form_id>\d+)/get/?$',
	    question_get),
	    
	url(r'^forms/(?P<form_id>\d+)/update/$',
	    update_field,
	    name='update_field_ajax'),

	url(r'^forms/(?P<form_id>\d+)/update/(?P<question_id>\d+)?$',
	    update_field,
	    name='update_field'),
	    
	url(r'^forms/(?P<form_id>\d+)/field_order/?$',
	    questions_update_order,
	    name='update_field_order'),
)
