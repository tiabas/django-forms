# -*- coding: utf-8 -*-
import re, uuid
from datetime import datetime
from django.db import models
from django.db.models import permalink
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify
from django.contrib.humanize.templatetags.humanize import ordinal
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.exceptions import ObjectDoesNotExist
from utils.model_utils import copy_model_instance
from utils.slugutils import unique_slugify
from django.utils.html import escape
from django.db.models import Q
from django.db.models import Sum

ACCESS_LEVEL = (
	('user', 'User'),
	('reviewer', 'Admin')
	)
	
QTYPE_CHOICES = (
	('number_input', 'Number Input'),
	('number_select', 'Number Select'),
	('text_input', 'Text Input'),
	('text_area', 'Text Area'),
	('time_input', 'Time'),
	('url_input', 'Website'),
	('email_input', 'Email'),
	('date_input', 'Date'),
	('select_box', 'Select List'),
	('radio_list', 'Radio List'),
	('checkbox_list', 'Checkbox List'),
	('section_break', 'Section Break'),
	('location_input', 'MapLocation'),	
)

MULTIPLE_CHOICE_FIELDS =['select_box', 'radio_list', 'checkbox_list']
NUMERIC_FIELDS =['number_input', 'number_select']

SENT, RECEIVED = range(2)
FORM_ACTIONS= (
	('SENT', 'Sent'),
	('RECEIVED', 'Received'),
)

def _unique_title(instance, value, title_field_name='title', title_separator='_'):

	title_field = instance._meta.get_field(title_field_name)
	title_len = title_field.max_length

class TemplateManager(models.Manager):
	
	def get_form(self, form_slug):
		try:
			return self.get(slug=form_slug)
		except ObjectDoesNotExist:
			return None
			
	def get_template(self, author, form_id):
		return self.get(pk=form_id, author=author)
		
	def all(self, author):
		return self.filter(author=author)
		
	def all_filled(self, user_id):
		return len(Answer.objects.filter(user=user_id).values('session_uuid').distinct())
	
	def all_deleted(self, author=None):
		if author:
			return self.filter(deleted=True)
		else:
			return self.filter(author=author, deleted=True)

	def all_active(self, user=None):
		if user:
			return Survey.objects.filter(Q(author=user, deleted=False) | Q(co_authors=user, deleted=False))
		else:
			return Survey.objects.filter(deleted=False)

	def all_public(self, author=None):
		if author:
			return self.filter(author=author, deleted=False, public=True)
		else:
			return self.filter(deleted=False, public=True)

	def num_deleted(self, author):
		return self.all_deleted(author).count()

	def num_active(self, author):
		return self.all_active(author).count()
	
class Survey(models.Model):
	
	title = models.CharField(max_length=255,
							help_text=_('Only use the following characters: a-z A-Z 0-9 _ -'))
	slug = models.SlugField("slug", max_length=140, unique=True)
	description = models.CharField(max_length=255,
							help_text=_('Short description of your survey (Limit 140 characters)'))
	author = models.ForeignKey(User,related_name="author")
	co_authors = models.ManyToManyField(User,verbose_name=_('co-authors'),
							related_name="co_authors",
							null=True, 
							blank=True)
	pub_date = models.DateTimeField(_('publish on'), 
							null=True, blank=True,
							help_text=_('Make this survey publicly available for copying'))
	exp_date = models.DateTimeField(_('close on'), 
							null=True, blank=True)
	public = models.BooleanField(default=False)
	restricted = models.BooleanField(default=True,
							help_text=_('check to restrict form to only authenticated users'))
	deleted = models.BooleanField(default=False)
	allows_multiple_interviews = models.BooleanField(verbose_name=_('Allow multiple submissions'),
							help_text=_('Check to allow users can make multiple submissions of this form'),
							default=True)
	confirmation_text = models.CharField(max_length=255,
							default='Success! Thanks for filling out my form!',
							help_text=_('Confirmation options for this form'))
	modified = models.DateTimeField(_('modified on'), auto_now=True)
	is_closed = models.BooleanField(_('close survey'), default=False)
	    
	objects = models.Manager()
	author_manager = TemplateManager()
	
	@property
	def answer_count(self):
		if hasattr(self, '_answer_count'):
			return self._answer_count
		self._answer_count = sum(q.answer_count for q in self.questions.iterator())
		return self._answer_count

	@property
	def session_key_count(self):
		self._submission_count = len(Answer.objects.filter(question__survey=self.id).values('session_key').distinct())
		return self._submission_count

	def get_questions(self):
		return self.questions.all().order_by('order')

	def make_copy(self, title, author):			
		dup_template = Survey(
				author=author,
				title=title,
				description=self.description,
				)
		dup_template.save()
		for q in self.questions.all():
			q.make_copy(dup_template)
		return dup_template
		
	@property
	def has_answers_from(self, session_key):
		return bool(Answer.objects.filter(session_key__exact=session_key.lower(),
		            question__survey__id__exact=self.id).distinct().count())

	@property
	def has_answers(self):
		return bool(Answer.objects.filter(question__survey__id__exact=self.id).distinct().count())

	def save(self, *args, **kwargs):
		if self.title and not self.slug or slugify(self.title) != self.slug:
			queryset= Survey.author_manager.all(self.author).exclude(pk=self.id)
			self.slug = unique_slugify(self, self.title, queryset=queryset)
		super(Survey, self).save(*args, **kwargs)

	def __unicode__(self):
		return self.title
		
	@models.permalink
	def get_absolute_url(self, user=None):
		return ('form_template_view', (), {'form_id': str(self.id)})

	#class Meta:
		#unique_together = ('slug','author')

class Question(models.Model):
	
	survey = models.ForeignKey(Survey, related_name="questions")
	# sub_field = models.ForeignKey(self, related_name="sub_fields", blank=True, null=True, default=None)
	text = models.CharField(max_length=300)
	hint = models.CharField(max_length=400, null=True, blank=True)
	creation_date = models.DateTimeField("date created",default=datetime.now)
	qtype = models.CharField(_('field widget type'), max_length=25, choices=QTYPE_CHOICES)#the widget type 
	qinputformat = models.SmallIntegerField(_('field data type'), max_length=2, choices=((0, 'Character'), (1, 'Numeric'), (2, 'Binary')), default=1)
	required = models.BooleanField(default=True)
	order = models.IntegerField(null=True, blank=True, default=0)
	access_level = models.CharField(_('Field Access'),default="user", max_length=20, choices=ACCESS_LEVEL)
	# Define if the user must select at least 'choice_num_min' number of
	# choices and at most 'choice_num_max'
	choice_num_min = models.IntegerField("minimum number of choices",null=True, blank=True)
	choice_num_max = models.IntegerField("maximum number of choices",null=True, blank=True)
	
	class Meta:
		unique_together = ('survey', 'text')

	@property
	def answer_count(self):
		if hasattr(self, '_answer_count'):
			return self._answer_count
		self._answer_count = self.answers.count()
		return self._answer_count
	
	def get_attribute(self, attr, default=None):
		try:
			value = self.field_attrs.get(attribute=attr).value
			return value
		except ObjectDoesNotExist:
			return default
			
	def is_multiple_choice(self):
		#TODO: This method of getting the form type seems crude to me
		#It would be nice to clean this up 
		if self.qtype in MULTIPLE_CHOICE_FIELDS:
			return True
		else:
			return False

	def is_numeric(self):
		#TODO: This method of getting the form type seems crude to me
		#It would be nice to clean this up 
		if self.qtype in NUMERIC_FIELDS:
			return True
		else:
			return False
			
	def get_type(self):
		return self.qtype
			
	def make_copy(self, form_template):
		new_question = copy_model_instance(self)
		new_question.survey = form_template
		new_question.save()
		if self.is_multiple_choice() and len(self.choices.all()):
			for choice in self.choices.all():
				c = copy_model_instance(choice)
				c.question = new_question
				c.save()
		return new_question

	def __unicode__(self):
		return escape(self.text)

	def get_absolute_url(self):
		return "/survey/question/%s" % (self.id)

class FieldAttribute(models.Model):
	
	template_field = models.ForeignKey(Question, related_name="field_attrs")
	attribute = models.CharField(max_length=30)
	value = models.CharField(max_length=30)
	
	def __unicode__(self):
		return "%s: %s" % (self.attribute, self.value)
	
class Choice(models.Model):

	question = models.ForeignKey(Question, related_name="choices")
	text = models.CharField(max_length=30)
	order = models.IntegerField(null=True,blank=True)
	
	def __unicode__(self):
		return self.text

	class Meta:
		unique_together = ('question', 'text')


class AnswerManager(models.Manager):
	
	def user_form_values(self, user_id, uuid, ):
		return self.filter(user=user_id, session_uuid=uuid).order_by('question__order').values('question__text', 'text')
	
	def get_answers_by_uuid(self, uuid):
		return self.filter(session_uuid=uuid).order_by('question__order')
		
	def get_sum_by_uuid(self, uuid):
		return self.filter(session_uuid=uuid).order_by('question__order').aggregate(Sum('text')).get('text__sum', 0)
		
class Answer(models.Model):
	user = models.ForeignKey(User, related_name="answers_by")
	question = models.ForeignKey(Question, related_name="answers")
	text = models.TextField(max_length=500)
	session_key = models.CharField(_("session key"), blank=True, null=True, max_length=40)
	session_uuid = models.CharField(_("Session unique identifier"), max_length=40)
	submission_date = models.DateTimeField("submitted on",default=datetime.now)
	
	objects = models.Manager()
	manager = AnswerManager()

	class Meta:
		unique_together = ('user', 'session_uuid', 'session_key')

	def __unicode__(self):
		return u"%s: %s" % (self.question, escape(self.text))

class FormSessionManager(models.Manager):
	#hack for getting all complteted forms
	def user_sessions(self, user_id):
		return self.filter(user=user_id).order_by('-modified')
	
	def new_form_session(self, user, form, commit=True):
		unique_session_uuid = ""
		while True:
			unique_session_uuid = uuid.uuid4().hex
			try:
				self.get(uuid=unique_session_uuid)
			except ObjectDoesNotExist:
				break
		# print unique_session_uuid
		unique_session = FormSession(
						user = user,
						form = form,
						uuid = unique_session_uuid
						)
		unique_session.save(commit)
		return unique_session
		
	def create_form_session(self, user, form, uuid):
		unique_session = FormSession(
						user = user,
						form = form,
						uuid = uuid
						)
		unique_session.save()
		return unique_session
	

class FormSession(models.Model):
	form = models.ForeignKey(Survey, related_name="form_sessions")
	user = models.ForeignKey(User, related_name="form_sessions")
	uuid = models.CharField(_("unique session identifier"), max_length=40)
	modified = models.DateTimeField(_('modified on'), auto_now=True)
	complete_date = models.DateTimeField(_('date of completion'), null=True, blank=True)
	complete = models.BooleanField(default=False)

	objects = models.Manager()
	manager = FormSessionManager()
		
	def __unicode__(self):
		return "%s: %s" % (self.form, self.uuid)

	def delete(self):
		for answer in Answer.manager.get_answers_by_uuid(self.uuid):
			answer.delete()
		super(FormSession, self).delete()
		

	class Meta:
		unique_together = ('form', 'user', 'uuid')
