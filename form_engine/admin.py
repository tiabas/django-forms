# -*- coding: utf-8 -*-
from django.contrib import admin
import django.contrib.contenttypes.generic
from form_engine.models import *

class FormSessionAdmin(admin.ModelAdmin):
	list_display = ('form', 'uuid', 'user', 'complete')
	list_filter = ('form', 'uuid', 'user', 'complete')
	
class FieldAttributeAdmin(admin.ModelAdmin):
	list_display = ('template_field', 'attribute', 'value')
	list_filter = ('template_field',)
	
class AnswerInline(admin.TabularInline):
	model = Answer

class AnswerAdmin(admin.ModelAdmin):
	list_display = ('user','question','text','submission_date','session_key','session_uuid')
	list_filter = ('session_key', 'session_uuid' )

class ChoiceAdmin(admin.ModelAdmin):
	list_display = ('text','question')
	fieldsets = [
	('Question',	{'fields': ['question']}),
	('Choice',	{'fields': ['text']}),
	('Order',	{'fields': ['order']}),
	]

class ChoiceInline(admin.TabularInline):
	model = Choice
	extra = 2 

class QuestionAdmin(admin.ModelAdmin):
	list_display = ('order', 'text','survey','creation_date','qinputformat','qtype')
	fieldsets = [
	('Survey',	{'fields': ['survey']}),
	('Required',{'fields': ['required']}),	
    ('Order',	{'fields': ['order']}),	
    ('Label',	{'fields': ['text']}),
	('Hint',	{'fields': ['hint']}),
	('Access',	{'fields': ['access_level']}),
	('Type',	{'fields': ['qtype']}),
	('Input Format',{'fields': ['qinputformat']}),
	]
	# inlines = [ChoiceInline]
	# inlines = [AnswerInline]

class QuestionInline(admin.TabularInline):
	model = Question
	extra = 2

    
class SurveyAdmin(admin.ModelAdmin):
	list_display = ('title','author','pub_date','slug')
	prepopulated_fields = {"slug": ("title",)}
	inlines = [
			QuestionInline
		]
	class Media:
		js= (
			'/site_media/genericadmin.js',
		)
admin.site.register(FieldAttribute, FieldAttributeAdmin)
admin.site.register(Survey, SurveyAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Choice,ChoiceAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(FormSession, FormSessionAdmin)