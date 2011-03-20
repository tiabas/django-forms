# -*- coding: utf-8 -*-
import uuid
from datetime import datetime
from datetime import date
from django.template.defaultfilters import slugify
from django.forms import BaseForm, Form, ValidationError
from django.forms import CharField, ChoiceField, SplitDateTimeField,\
                            CheckboxInput, BooleanField,FileInput,\
                            FileField, ImageField, Textarea, TextInput, Select, RadioSelect,\
                            CheckboxSelectMultiple, MultipleChoiceField,\
                            SplitDateTimeWidget,MultiWidget, MultiValueField
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.template import Context, loader, Template
from django.forms.extras.widgets import *
from django.forms.forms import BoundField
from django.core.exceptions import ValidationError
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape

from form_engine.customWidgets import PlainText, TimeInputWidget,\
                            CustomRadioRenderer, CustomCheckboxSelectMultiple,\
							LocationWidget, SplitSelectDateTimeWidget
from form_engine.customFields import *
from form_engine.models import *

MAX_CHOICE_LEN = 30
Q_CHOICE_NUM = 4
MULTIPLE_CHOICE_FIELDS =['select_box', 'radio_list', 'checkbox_list']

class BaseResponseForm(forms.Form):
	
	def __init__(self, question, survey, user, session_uuid=None, session_key=None, edit_existing=True, *args, **kwdargs):
		self.question = question
		self.survey = survey
		self.answer = None
		self.user = user
		self.session_uuid = session_uuid
		self.field_attrs = dict([(attr.attribute, attr.value) for attr in question.field_attrs.all()])
		initial = None
		if session_key:
			self.session_key = session_key.lower()
		else:
			self.session_key = None
		if self.session_uuid and edit_existing:
			query = question.answers.filter(session_uuid=self.session_uuid)
			# if not user.is_authenticated():
			# 	query = question.answers.filter(session_uuid=self.session_uuid)
			# else:
			# 	query = question.answers.filter(session_uuid=self.session_uuid)
			if query.count():
				self.answer = query[0]
				initial = self.answer.text
				if not 'initial' in kwdargs:
					kwdargs['initial'] = {}
				if not 'answer' in kwdargs['initial']:
					kwdargs['initial']['answer'] = self.answer.text
		super(BaseResponseForm, self).__init__(*args, **kwdargs)
		self.fields['answer'].required = self.question.required
		self.fields['answer'].label = self.question.text
		if not self.question.required:
			self.fields['answer'].help_text = _('This question is optional')

	"""use this template if the survey form is to be pre-rendered rather than created
	during the page rendering"""
	def as_template(self):
		"Helper function for rendering a form field as a template element. All inputs are disabled"
		bound_fields = [BoundField(self, field, name) for name, field in self.fields.items()]
		c = Context(dict(form = self, bound_fields = bound_fields))
		t = Template('''
			<li class="sortable_item" id="bar_{{ form.question.id }}">
			<span id="qn_attr" class="icon">
			<a href="{% url update_field form_id=form.survey.id question_id=form.question.id %}" id="updlstItem{{ form.question.id }}" class="updField">
				<img class="icon_button" src="/form_media/images/edit.png"/>
			</a>
			<a href="{% url delete_field form_id=form.survey.id question_id=form.question.id %}" id="dellstItem{{ form.question.id }}" class="delField">
				<img class="icon_button" src="/form_media/images/delete.gif"/>
			</a>
			<img src="/form_media/images/arrow.png" alt="move" width="16" height="16" class="icon_button handle" />
			</span>
			<span id="qLabel_{{ form_pair.q_id }}" class="qlabel"> {{ form.answer.label_tag }} </span>
			<span class="helpText">{{ form.question.hint }}</span>
			<div class="options">{{ form.answer }}</div>
			</li>
				''')
		return t.render(c)

	def as_input_field(self):
		"Helper function for rendering each form field as submittable input element"
		bound_fields = [BoundField(self, field, name) for name, field in self.fields.items()]
		c = Context(dict(form = self, bound_fields = bound_fields))
		t = Template('''
				<li id="bar_{{ form.question.id }}">
					<span id="qLabel_{{ form_pair.q_id }}" class="qlabel"> {{ form.answer.label_tag }}</span>
					<span class="helpText">{{ form.question.hint }}</span>
					<div class="options">{{ form.answer }} {% if form.errors %}<span>{{form.answer.errors}}</span>{% endif %}</div>
				</li>
			''')
		return t.render(c)

	# def clean_answer(self):
	# 	if 'answer' in self.cleaned_data:
	# 		ans = self.cleaned_data['answer']
	# 	#TODO: escape answer user input
	# 	return ans

	def save(self, commit=True):
		if self.cleaned_data['answer'] is None:
			if self.fields['answer'].required:
				raise ValidationError(_('This field is required.'))
			return
		usr_response = self.answer
		if usr_response is None:
			usr_response = Answer()
		usr_response.question = self.question
		usr_response.session_key = self.session_key
		if self.user.is_authenticated():
			usr_response.user = self.user
		else:
			raise ValidationError(_('You must be logged in'))
		usr_response.session_uuid = self.session_uuid
		usr_response.text = mark_safe(self.cleaned_data['answer'])
		if commit: usr_response.save()
		return usr_response
		
class EmailInputField(BaseResponseForm):
	answer = forms.EmailField(widget=TextInput(attrs={'class':'text'}))

class URLInputField(BaseResponseForm):
	answer = forms.URLField(widget=TextInput(attrs={'class':'text'}))

class TimeInputField(BaseResponseForm):
	answer = forms.CharField(widget=TimeInputWidget(attrs={'class':'text'}))

class DateInputField(BaseResponseForm):
	answer = forms.DateField(widget=SelectDateWidget(attrs={'class':'text'}, years=range(1900,2020)))

class NumberField(BaseResponseForm):
	answer = forms.IntegerField()
	
	def __init__(self, *args, **kwargs):
		super(NumberField, self).__init__(*args, **kwargs)
		self.fields['answer'].widget = TextInput(attrs=self.field_attrs)
		
class NumberSelectField(BaseResponseForm):
	answer = forms.IntegerField()
	
	def __init__(self, *args, **kwargs):
		super(NumberSelectField, self).__init__(*args, **kwargs)
		self.min_value = int(self.question.get_attribute('min_value', 0))
		self.max_value =int(self.question.get_attribute('max_value', 45))
		self.choices = tuple([(x, x) for x in range(self.min_value, self.max_value+1)])
		self.fields['answer'].widget = Select(choices=self.choices)
	
class TextInputField(BaseResponseForm):
	answer = forms.CharField(widget=TextInput(attrs={'class':'text'}))

class TextAreaField(BaseResponseForm):
	answer = forms.CharField(widget=Textarea(attrs={'class':'textarea'}))
	
class LocationField(BaseResponseForm):
	answer = LocationField(widget=LocationWidget(map_width=350, map_height=300, attrs={'class':'text'}))

class OptionForm(BaseResponseForm):
	answer = forms.Field()

	def __init__(self, *args, **kwdargs):
		super(OptionForm, self).__init__(*args, **kwdargs)
		self.choices = []
		self.choices_dict = {}
		self.initial['answer'] = None
		self.initial_response = None
		self.field_choices = self.question.choices.all()
		if len(self.field_choices):
			for choice in self.field_choices:
				if self.answer and self.answer.text == choice.text:
					self.initial_response = choice.id
				self.choices.append((str(choice.id), choice.text))
				self.choices_dict[str(choice.id)] = str(choice.text)
		self.initial['answer'] = self.initial_response

	def clean_answer(self):
		key = self.cleaned_data['answer']
		if not key and self.fields['answer'].required:
			raise ValidationError, _('This field is required.')
		return self.choices_dict.get(key,key) #look at dict get() method

class SelectListField(OptionForm):
	def __init__(self, *args, **kwdargs):
		super(SelectListField, self).__init__(*args, **kwdargs)
		self.fields['answer'].widget = Select(choices=self.choices)

class RadioListField(OptionForm):
	def __init__(self, *args, **kwdargs):
		super(RadioListField, self).__init__(*args, **kwdargs)
		self.fields['answer'].widget = RadioSelect(renderer=CustomRadioRenderer, choices=self.choices, attrs={'class':'radio'})

class CheckListField(OptionForm):
	def __init__(self, *args, **kwdargs):
		session_uuid = kwdargs.get('session_uuid', False)
		self.answers_text = []
		super(CheckListField, self).__init__(*args, **kwdargs)
		if session_uuid:
			self.answers_text = [answer.text for answer in self.question.answers.filter(session_uuid=session_uuid)]
			self.initial_response = ["%s" % choice.id for choice in self.question.choices.filter(text__in=self.answers_text)]
			self.initial['answer'] = self.initial_response
		self.current_choices = ["%s" % choice.id for choice in self.field_choices]
		self.fields['answer'] = MultipleChoiceField(
					label=self.question.text,
					widget=CustomCheckboxSelectMultiple, 
					choices=self.choices,
					required=False)

	def clean_answer(self):
		keys = self.cleaned_data['answer']
		if not keys and self.fields['answer'].required:
			raise ValidationError, _('This field is required.')
		for key in keys:
			if not key and self.fields['answer'].required:
				raise ValidationError, _('Invalid Choice.')
		return self.cleaned_data['answer']

	def save(self, commit=True):
		ans_list = []
		for choice_id in self.cleaned_data['answer']:
			prev_choice = self.choices_dict.get(choice_id, False)
			if not prev_choice in self.answers_text:
				ans = Answer(
					user=self.user,
					question=self.question,
					session_key = self.session_key,
					session_uuid=self.session_uuid,
					text=prev_choice
				)
				ans.save()
				ans_list.append(ans)
		for choice_id in self.current_choices:
			if not choice_id in self.cleaned_data['answer']:
				try:
					ans = Answer.objects.get(session_uuid=self.session_uuid, question=self.question, text=self.choices_dict.get(choice_id, ""))
					ans.delete()
				except ObjectDoesNotExist:
					pass
		return ans_list

class SectionBreakField(BaseResponseForm):
	answer = forms.CharField(widget=PlainText(),
							help_text=_('Section sub-title goes here'))
	
	def __init__(self, *args, **kwdargs):
		self.title = CharField(widget=PlainText(), initial='')
		super(SectionBreakField, self).__init__(*args, **kwdargs)
		
	# Helper function for rendering a form element with only plain text
	def as_template(self):
		bound_fields = [BoundField(self, field, name) for name, field in self.fields.items()]
		c = Context(dict(form = self, bound_fields = bound_fields))
		t = Template('''
		<li class="sortable_item" id="bar_{{ form.question.id }}">
			<span id="qn_attr" class="icon">
			<a href="{% url update_field form_id=form.survey.id question_id=form.question.id %}" id="updlstItem{{ form.question.id }}" class="updField">
			<img class="icon_button" src="/form_media/images/edit.png"/></a>
			<a href="{% url delete_field form_id=form.survey.id question_id=form.question.id %}" id="dellstItem{{ form.question.id }}" class="delField">
			<img class="icon_button" src="/form_media/images/delete.gif"/></a>
			<img src="/form_media/images/arrow.png" alt="move" width="16" height="16" class="icon_button handle" />
			</span>
			<div class="section">
			<span class="title" >{{ form.answer.label_tag }}</span><br />
			<span class="sub-title">{{ form.question.hint }}</span>
			</div>
		</li>
			''')
		return t.render(c)
			
	# Helper function for rendering a form element with only plain text
	def as_input_field(self):
		bound_fields = [BoundField(self, field, name) for name, field in self.fields.items()]
		c = Context(dict(form = self, bound_fields = bound_fields))
		t = Template('''
		<li id="bar_{{ form.question.id }}">
			<div class="section">
			<span class="title" >{{ form.answer.label_tag }}</span><br />
			<span class="sub-title">{{ form.question.hint }}</span>
			{{ form.errors }}
			{% if form.answer.required %}is required{% endif %}
			</div>
		</li>
			''')
		return t.render(c)

	# We do not save input for this field because it is not supposed to take any
	def save(self):
		pass

FORM_Q_TYPE = {
	'number_input': NumberField,
	'number_select':NumberSelectField,
	'text_input': TextInputField,
	'text_area': TextAreaField,
	'time_input': TimeInputField,
	'date_input': DateInputField,
	'email_input': EmailInputField,
	'url_input': URLInputField,
	'select_box': SelectListField,
	'radio_list': RadioListField,
	'checkbox_list': CheckListField,
	'section_break': SectionBreakField,
	'location_input': LocationField,
}
	
def forms_for_survey(request, survey, session_uuid=None, edit_existing=True, prefix=None):
	"""
	returns a list contianing form objects that will be added to the survey form.
	each form is defined y it's prefix and specified by the "prefix" parameter.
	In this particular case, the prefix is made up of the suvey id and question id.
	This prefix is used angain when collecting data and helps django know what data
	is for what form.
	"""
	sp = "%s_" % str(survey.id)
	if prefix:
		sp = "%s%s" % (sp, prefix)
	
	session_key = request.session.session_key.lower()
	user = request.user
	if request.method == "POST" and request.POST: # bug in forms
		post_data = request.POST
	else:
		post_data = None
	print session_uuid
	return [FORM_Q_TYPE[question.qtype](question, survey, user, session_uuid=session_uuid, session_key=session_key,
	 		prefix=sp+str(question.id), data=post_data, edit_existing=edit_existing)
			for question in survey.questions.all().order_by('order')]
	
def forms_for_survey_no_prefix(request, survey):
	user = request.user
	return [FORM_Q_TYPE[question.qtype](question, survey, user)
			for question in survey.questions.all().order_by('order')]

def form_for_question(question, survey):
	question = Question.objects.get(id=question.id, survey=survey.id)
	return FORM_Q_TYPE[question.qtype](question, survey)

def forms_for_question():
	formlistdict = {}
	formlistdict['question'] = [QuestionAddForm()]
	formlistdict['choices'] = [ChoiceAddForm(prefix="choice_"+str(x)) for x in range(Q_CHOICE_NUM)]
	return formlistdict

class SurveyCreateForm(Form):
	title = forms.CharField(
				max_length=20,
				label=u"Title",
				help_text=u"Only use the following characters: a-z A-Z 0-9 _ -"
				)
	exp_date = forms.DateField(label=u"Closing date")
	public = forms.BooleanField(
				required=True,
				help_text=u"Make this survey publicly available"
				)
	restricted = forms.BooleanField(
				required=True,
				help_text=u"Make this survey restricted to certain users"
				)
	description = forms.CharField(
				max_length=300,
				widget=forms.Textarea,
				help_text=u"Short description of your survey"
				)
	#complete = forms.BooleanField(required=False)
	#co_authors = forms.ManyToManyField(User,null=True,blank=True)
	#takers = forms.ManyToManyField(User,null=True,blank=True)
	#pub_date = forms.DateTimeField("date published",default=datetime.now)

	def save(self):
		survey = Survey(
				title=self.cleaned_data['title'],
				description=self.cleaned_data['description'],
				exp_date=self.cleaned_data['exp_date'],
				restricted=self.cleaned_data['exp_date'],
				public=self.cleaned_data['public']
				)
		survey.save()
		return survey

class BaseFieldForm(Form):
	text = forms.CharField(
				label=u"Field Label",
				widget=forms.Textarea(attrs={'class':'textarea'})
				)
	hint = forms.CharField(
				max_length=400,
				label=u"Instructions to user",
				required=False,
				widget=forms.Textarea(attrs={'class':'textarea'})
				)
	required = forms.BooleanField(
				initial=True,
				label=u"Required",
				help_text=u"Unheck if this question is optional",
				required=False,
				)
	qtype = forms.CharField(
				label=u"Field Type",
				widget=forms.HiddenInput()
				)
	access =  forms.ChoiceField(
				label=_('Show Field to'),
				initial="user", 
				choices=ACCESS_LEVEL,
				)

	def __init__(self, field_type, instance=None, *args, **kwdargs):
		self.instance = instance
		super(BaseFieldForm, self).__init__(*args, **kwdargs)
		self.init_attrs = {}
		if self.instance:
			self.init_attrs =  dict([(f.name, f.value_from_object(self.instance)) for f in self.instance._meta.fields])
			for f_name, f_obj in self.fields.items():
				if not self.initial.get(f_name, False): 
					self.initial[f_name] = self.init_attrs.get(f_name, None) 
		self.initial['qtype'] = field_type
		self.extra_attrs = []

	def save(self, form_template, *args, **kwargs):
		text = mark_safe(self.cleaned_data['text'])
		hint = mark_safe(self.cleaned_data['hint'])
		if self.instance:
			self.instance.text = text
			self.instance.required = self.cleaned_data['required']
			self.instance.hint = hint 
			self.instance.save()
			if len(self.extra_attrs):
				for attribute in self.extra_attrs:
					if not self.cleaned_data[attribute] is None:
						try:
							template_field_attr = self.instance.field_attrs.get(attribute=attribute)
							template_field_attr.value = self.cleaned_data[attribute]
						except ObjectDoesNotExist:
							template_field_attr = FieldAttribute(
											template_field=template_field,
											attribute=attribute,
											value=self.cleaned_data[attribute]
											)
						template_field_attr.save()
			return self.instance
		else:
			template_field = Question(
					survey=form_template,
					text=text,
					qtype=self.cleaned_data['qtype'],
					hint=hint,
					required=self.cleaned_data['required']
					)
			template_field.save()
			if len(self.extra_attrs):
				for attribute in self.extra_attrs:
					if not self.cleaned_data[attribute] is None:
						template_field_attr = FieldAttribute(
										template_field=template_field,
										attribute=attribute,
										value=self.cleaned_data[attribute]
										)
						template_field_attr.save()
			return template_field
	
class IntegerFieldForm(BaseFieldForm):

	def __init__(self, *args, **kwdargs):
		super(IntegerFieldForm, self).__init__('number_input', *args, **kwdargs)
		self.extra_attrs = ['min_value', 'max_value']
		self.init_min = 0
		self.init_max = 10
		if self.instance:
			self.init_min = self.instance.get_attribute('min_value', 0)
			self.init_max = self.instance.get_attribute('max_value', 0)
		self.fields['min_value'] = forms.IntegerField(
								initial= self.init_min,
								required=False, 
								widget=TextInput(attrs={'class':'numeric'})
								)
		self.fields['max_value'] = forms.IntegerField(
								initial= self.init_max,
								required=False, 
								widget=TextInput(attrs={'class':'numeric'},)
								)

class IntegerSelectFieldForm(IntegerFieldForm):
	def __init__(self, *args, **kwdargs):
		super(IntegerSelectFieldForm, self).__init__(*args, **kwdargs)
		self.initial['qtype'] = 'number_select'

class TextFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(TextFieldForm, self).__init__('text_input', *args, **kwdargs)
		self.extra_attrs = ['predefined_value']
		self.init_value = ""
		if self.instance:
			self.init_value = self.instance.get_attribute('predefined_value', '')
		self.fields['predefined_value'] = forms.CharField(
								initial= self.init_value,
								required=False, 
								widget=TextInput(attrs={'class':'text'})
								)


class TextAreaFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(TextAreaFieldForm, self).__init__('text_area', *args, **kwdargs)
		
class TimeFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(TimeFieldForm, self).__init__('time_input', *args, **kwdargs)
		
class DateFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(DateFieldForm, self).__init__('date_input', *args, **kwdargs)
		
class EmailFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(EmailFieldForm, self).__init__('email_input', *args, **kwdargs)

class URLFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(URLFieldForm, self).__init__('url_input', *args, **kwdargs)

class LocationFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(LocationFieldForm, self).__init__('location', *args, **kwdargs)

class SectionBreakFieldForm(BaseFieldForm):
	def __init__(self, *args, **kwdargs):
		super(SectionBreakFieldForm, self).__init__('section_break', *args, **kwdargs)
		self.fields['required'].widget = forms.widgets.HiddenInput()
		self.initial['required'] = False
		
class ChoiceWidget(TextInput):
	def render(self, *args, **kwargs):
		output = super(ChoiceWidget, self).render(*args, **kwargs)
		html = mark_safe(_('<li>'))
		html += output
		html += mark_safe(_('''
				<a id="addChoice" class="uiButton" style="width:25px"><b>+</b></a>
				<a id="delChoice" class="uiButton" style="width:25px"><b>-</b></a>
				</li>
				'''))
		return html
	
class MultipleChoiceFieldForm(BaseFieldForm):

	def __init__(self, *args, **kwdargs):
		self.num_choices = kwdargs.pop('choices', 5)
		super(MultipleChoiceFieldForm, self).__init__(*args, **kwdargs)
		self.choice_set = []
		if self.instance:
			self.choice_set = self.instance.choices.all()
			if len(self.choice_set) > 0:
				for choice in self.choice_set:
					self.fields['choice-%d' % choice.pk] = forms.CharField(
						label='Choices', 
						required=False,
						initial=choice.text,
						widget=ChoiceWidget(attrs={'class': 'choices'})
					)
		else:
			self.fields['newChoices'] = forms.CharField(
				label='Choices', 
				required=False,
				widget=ChoiceWidget(attrs={'class': 'choices'})
			)

	def save(self, *args, **kwdargs):
		template_field = super(MultipleChoiceFieldForm, self).save(*args, **kwdargs)
		new_choices = self.data.getlist('newChoices')
		del_choices = self.data.getlist('delChoices')
		for choice_key, choice_value in self.cleaned_data.iteritems():
			if u"choice-" in choice_key:
				_id = choice_key.split("-")[1]
				_text = choice_value
				try:
					choice = template_field.choices.get(id=_id)
					if len(del_choices) and choice_key in del_choices:
						choice.delete()
					else:
						choice.text = _text
						choice.save()
				except ObjectDoesNotExist:
					pass
		if len(new_choices):
			for choice_text in new_choices:
				if choice_text:
					choice = Choice(
						question=template_field,
						text=choice_text )
					choice.save()
		return template_field

class SelectListFieldForm(MultipleChoiceFieldForm):

	def __init__(self, *args, **kwdargs):
		super(SelectListFieldForm, self).__init__('select_box', *args, **kwdargs)

class CheckListFieldForm(MultipleChoiceFieldForm):
	def __init__(self, *args, **kwdargs):
		super(CheckListFieldForm, self).__init__('checkbox_list', *args, **kwdargs)

class RadioListFieldForm(MultipleChoiceFieldForm):
	def __init__(self, *args, **kwdargs):
		super(RadioListFieldForm, self).__init__('radio_list', *args, **kwdargs)
		
FIELD_TYPE_FORM = {
	'number_input': IntegerFieldForm,
	'number_select': IntegerSelectFieldForm,
	'text_input': TextFieldForm,
	'text_area': TextAreaFieldForm,
	'time_input': TimeFieldForm,
	'date_input': DateFieldForm,
	'email_input': EmailFieldForm,
	'section_break': SectionBreakFieldForm,
	'url_input': URLFieldForm,
	'location_input': LocationFieldForm,
	'select_box': SelectListFieldForm,
	'radio_list': RadioListFieldForm,
	'checkbox_list': CheckListFieldForm,
}

def get_form_for_field_type(field_type, instance=None, *args, **kwargs):
	field_type_form = FIELD_TYPE_FORM.get(field_type, None)
	if field_type_form is not None:
		return field_type_form(instance=instance, *args, **kwargs)
	return None
	
class ImportFormTemplateForm(Form):
	
	title = forms.CharField(
				max_length=200,
				label=u"Title",	
				widget=forms.TextInput(attrs={'class':'textarea', 'cols': 35, 'rows': 10}),
				help_text="Enter a title for your form"
				)
				
	def __init__(self, *args, **kwdargs):	
		self.current_user = kwdargs.pop('user', None)
		self.source_template = kwdargs.pop('source_template', None)
		super(ImportFormTemplateForm, self).__init__(*args, **kwdargs)		
		
	def clean_title(self):
		title = self.cleaned_data['title']
		slugified_title = slugify(title)
		try:
			Survey.objects.get(slug=slugified_title, author=self.current_user)
			raise forms.ValidationError("This title is already in use. Please enter a different one.")
		except ObjectDoesNotExist:
			return title
			
	def save(self):
		new_form = self.source_template.make_copy(self.cleaned_data['title'], self.current_user )
		return new_form
		
class QuestionModelForm(forms.ModelForm):
	text = forms.CharField(
				max_length=200,
				label=u"Field title",	
				widget=forms.Textarea(attrs={'class':'textarea', 'cols': 35, 'rows': 10})
				)
	qtype = forms.ChoiceField(
				label=u"Field type",
				choices=QTYPE_CHOICES,	
				widget=forms.HiddenInput()
				)
	hint = forms.CharField(
				max_length=400,
				label=u"Instructions to user",
				required=False,
				widget=forms.Textarea(attrs={'class':'textarea', 'cols': 35, 'rows': 10})
				)
	required = forms.BooleanField(
				initial=True,
				label=u"Required",
				help_text=u"Unheck if this question is optional",
				)
	class Meta:
		model = Question
		exclude = ('survey','creation_date', 'order', 'choice_num_min','choice_num_max')

class SurveyModelForm(forms.ModelForm):
	title = forms.CharField(
				max_length=150,
				widget=forms.TextInput(attrs={'tabindex': '1'}),
				label=u"Title",
				help_text=u"Only use the following characters: a-z A-Z 0-9 (100 chars max)"
				)
				
	description = forms.CharField(
				max_length=255,
				widget=forms.Textarea(attrs={'tabindex': '2', 'class':'textarea', 'cols': 35, 'rows': 10}),
				required=False,
				help_text=u"Short description of your survey (Limit 140 characters)"
				)
	public = forms.BooleanField(
				label=_('Make public'),
				required=False,
				widget=forms.CheckboxInput(attrs={'tabindex': '3'}),
				help_text=u"Make this survey publicly available for copying"
				)
	# co_authors = MultipleChoiceField(
	# 				label='Add co-authors',
	# 				widget=CustomCheckboxSelectMultiple, 
	# 				choices=self.choices,
	# 				required=False)
	# restricted = forms.BooleanField(
	# 				help_text=u"Make this survey restricted to certain authenticated users"
	# 				)
	# pub_date = forms.SplitDateTimeField(
	# 			required=False,
	# 			label=_('Publish on'),
	# 			help_text=_('DD-MM-YYYY'),
	# 			widget=SplitSelectDateTimeWidget(),
	# 			)
	# exp_date = forms.SplitDateTimeField(label=_('Close on'),
	# 			required=False,
	# 			help_text=_('DD-MM-YYYY'),
	# 			widget=SplitSelectDateTimeWidget(),
	# 			)

	class Meta:
		model = Survey
		exclude = ('author','complete', 'pub_date', 'exp_date', 'slug', 'deleted', 'co_authors')
		# fields = ['title','description','public']
		#widgets = {
			#'description': forms.Textarea(attrs={'cols': 50, 'rows': 20}),
			#}
	#def clean(self):
		#title_slug = slugify(self.cleaned_data.get("title"))
		#if not hasattr(self,"instance"):
			#if not len(Survey.objects.filter(slug=title_slug))==0:
				#raise ValidationError, _('The title of the survey must be unique.')
		#elif self.instance.title != self.cleaned_data.get("title"):
			#if not len(Survey.objects.filter(slug=title_slug))==0:
				#raise ValidationError, _('The title of the survey must be unique.')
		#return self.cleaned_data

class ChoiceForm(Form):
	text = forms.CharField(
				max_length=30,
				label=u"Choice",
				#help_text=u"Enter a choice for this question field",
				widget=forms.TextInput(attrs={'class':'text'})
				)
	"""
	order = forms.IntegerField(
				required=False,
				label=u"Order",
				#help_text=u"Order in which choice will be displayed (Not required)"
				)
	"""

	def save(self, *args, **kwargs):
		choice = Choice(
				text=self.cleaned_data['text'],
				#order=self.cleaned_data['order']
				)
		return choice