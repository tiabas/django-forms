# -*- coding: utf-8 -*-
# Create your views here.
import uuid
import simplejson
from django.db.models import Q, AutoField
from django.db import transaction
from django.conf import settings
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponseNotFound
from django.template import loader, RequestContext, Context, Template
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404, render_to_response
from django.utils.translation import ugettext_lazy as _
from django.utils import simplejson
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.admin.views.decorators import staff_member_required

from apps.form_engine.models import *
from apps.form_engine.forms import *
from apps.form_engine.decorators import authorize_form
from apps.form_engine.models import QTYPE_CHOICES

SELECT_FIELDS = ['select_box', 'radio_list', 'checkbox_list']

@login_required	
def view_public_templates(request,
				template_name='form_engine/public_forms.html'):
				
	public_templates = Survey.objects.filter(public=True)
	variables= RequestContext(request, {
		'request': request,
		'public_templates': public_templates,
	})	
	return render_to_response(template_name,variables)

@login_required
@transaction.commit_on_success
def import_form_template(request,
				template_slug,
				template_name='form_engine/import_template.html'):
	
	template = get_object_or_404(Survey, slug=template_slug)
	form = ImportFormTemplateForm(request.POST or None, user=request.user, source_template=template)
	if request.method == 'POST' and form.is_valid():
		dup_template = form.save()
		return HttpResponseRedirect(reverse('forms_home'))
		
	variables= RequestContext(request, {
		'request': request,
		'template': template,
		'form': form,
	})
	return render_to_response(template_name,variables)

@login_required
@transaction.commit_on_success
def add_field_type(request, form_id, field_type,
					template_name='form_engine/update_field.html'):
	
	template_field_form = get_form_for_field_type(field_type)
	if not template_field_form:
		raise HttpResponseNotFound("<p>Invalid field type: </p>" % request.POST.get('qtype'))
	form_template = get_object_or_404(Survey, pk=form_id)
	item_forms = forms_for_survey_no_prefix(request, form_template)
	if request.method == 'POST':
		response_dict = {}
		template_field_form = get_form_for_field_type(field_type, None, data=request.POST or None)
		if template_field_form.is_valid():
			new_template_field = template_field_form.save(form_template=form_template)
			if request.is_ajax():
				new_field = render_to_string('form_engine/field_list_item.html', {
								 'question_obj': new_template_field,
								 'survey': form_template
								})
				response_dict.update({'success': True, 'template_field': new_field})
				return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')
			return HttpResponseRedirect(reverse('form_template_edit',  kwargs={'form_id': form_template.id}))
		else:
			if request.is_ajax():
				response_dict.update({'success': False})
				t = Template('''
					<ul>
					{% for field in question_form  %}
						<li class="form_field">{{ field.label_tag }} {{ field }}</li>
						{% if field.errors %}
						<li>{{ field.errors }}</li>
						{% endif %}
					{% endfor %}
					<li><button type="submit" id="saveQuestion" name="saveForm" class="btTxt submit" >save</button></li>
					</ul>
				''')
				c = Context({'form': add_field_form})
				response_dict.update({'success': False, 'rendered_form': t.render(c)})
				return HttpResponse(simplejson.dumps(response_dict), mimetype='application/javascript')
			
	variables= RequestContext(request, {
				'request': request,
				'form_template': form_template,
				'item_forms': item_forms,
				'question_form': template_field_form,
				'field_type':field_type,
			})
	return render_to_response(template_name,variables)

@login_required
@transaction.commit_on_success
def update_field(request, form_id, question_id,
					template_name='form_engine/update_field.html'):
	"""
	Params: form id, question id

	Action: if the form has been submited update the question text first
		iterate over each of the choices that has been submitted
		choices that have been marked for deletion will be deleted permanently
		choices the have been marked as "newChoices" will be added to the database

	Return: if method is ajax, return ajax reponse
		otherwise, redirect to form detail page
	"""
	form_template = get_object_or_404(Survey, pk=form_id)
	item_forms = forms_for_survey_no_prefix(request, form_template)
	try:	
		template_field = Question.objects.get(id=question_id, survey=form_template)
	except ObjectDoesNotExist:
		return HttpResponse("the field you are trying to add has been deleted")
	template_field_update_form = get_form_for_field_type(template_field.qtype, template_field, data=request.POST or None)
	if template_field_update_form is None:
		return HttpResponse("form type is not valid")
	if request.method == "POST":
		postdata = request.POST.copy()
		if template_field_update_form.is_valid():
			template_field_update_form.save(form_template)
			return HttpResponseRedirect(reverse('form_template_edit', kwargs={'form_id': form_template.id}))
	field_choices = template_field.choices.all()
	variables = RequestContext(request, {
					'request': request,
					'form_template': form_template,
					'item_forms': item_forms,
					'question': template_field,
					'question_form': template_field_update_form,
					'field_choices': field_choices
					})
	if request.is_ajax():
		ajax_response = render_to_string('form_engine/field_update_form.html', variables)
		return HttpResponse(ajax_response)
	return render_to_response(template_name, variables)

@login_required
@transaction.commit_on_success
def question_delete(request, form_id):
	"""
	Takes the form_template id of selected question. Retrieves question id from ajax
	submitted POST data.
	"""
	if request.method == 'POST':
		question_id = request.POST.get('question_id', False)
		
		form_template = get_object_or_404(Survey, pk=form_id)
		if request.user != form_template.author:
			return HttpResponseForbidden()
		response_dict = {}
		try:
			question = Question.objects.get(id=question_id, survey=form_template)
			question.delete()
			response_dict.update({'success': 'true'})
			response_dict.update({'result': "Field successfully deleted."})
		except ObjectDoesNotExist:
			response_dict.update({'success': 'false'})
			response_dict.update({'result': "Field does not exist!"})
			if not request.is_ajax():
				return HttpResponseNotFound()
		if request.is_ajax():
			return HttpResponse(simplejson.dumps(response_dict))
		else:
			return HttpResponseRedirect(reverse('form_template_edit', kwargs={'form_id': form_template.id}))

@login_required
def question_get(request,form_id):
	if request.method == "GET":
		request_get = request.GET.copy()
		question = Question.objects.get(id=request_get['q_id'], survey=form_id)
		response_dict = {"id": question.id,"text": question.text, "type": question.qtype, "required": question.required }
		if request.is_ajax():
			return HttpResponse(simplejson.dumps(response_dict), mimetype='application/json')
		else:
			return HttpResponse("Request can only be made asynchronously!")

@login_required
@transaction.commit_on_success
def questions_update_order(request,form_id):
	"""
	Params: magicform id, question id
	
	Action: redefines the order numbers for all fields within a given survey so that they are diplayed according
		to how the how the user places fields that have been dragged out of position.
	
	Return:	A message indicating whether the action was successful or not
	TODO:	Error checking; since the re-order relies heavily on the fact that the submitted data does not have it's
	array indices modified during transfer. A better way that guarantees order integrity is necessary
	"""
	magicform = get_object_or_404(Survey, id=form_id)
	if request.method == "POST":
		field_list = request.POST.getlist('field')
		field_order_dict = dict([(field_list[position],position) for position in range(len(field_list))])
		for field_id, position in field_order_dict.iteritems():
			try:
				question = Question.objects.get(id=field_id,survey=form_id)
			except ObjectDoesNotExist:
				HttpResponse("One or more of the field id's is invalid!")
			question.order = position
			question.save()
		return HttpResponse("Fileds successfully reordered!")
	return HttpResponse("Re-ordering failed!")

@login_required
@transaction.commit_on_success
def choice_add(request,question_id):
	question = get_object_or_404(Question, id=question_id)
	if request.method == "POST":
		request_post = request.POST.copy()
		choice_form = ChoiceForm(data=request_post)
		if choice_form.is_valid():
			new_choice = choice_form.save(commit=False)
			new_choice.question = question
			new_choice.save()
			return HttpResponseRedirect(reverse("survey-edit",None,(),{"survey_slug":question.survey.slug}))
	choice_form = ChoiceForm()
	return render_to_response(template_name,
				{'title': _("Add a choice"),
				'form' : choice_form},
				context_instance=RequestContext(request))


@login_required
@transaction.commit_on_success
def save_form_field(request, form_id,
						template_name='form_engine/field_list_item.html'):
	"""
	Params: form id

	Action: if the form has been submited checks that it is valid and
		creates a new field object. Checks if the question had choices,
		creates the necessary choice objects, assigns a field id to
		each of them and finally commits them to the database.

	Return: if method is ajax, returns ajax reponse else returns original view
	"""
	magicform = get_object_or_404(Survey, pk=form_id)
	if request.method == 'POST':
		field_type = request.POST.get('qtype', False)
		if field_type:
			form = get_form_for_field_type(field_type, request.POST)
		else:
			raise HttpResponseNotFound("<p>Invalid field type: </p>" % request.POST.get('qtype'))
		if form.is_valid():
			new_template_field = form.save(form_template=magicform)
			if request.is_ajax():
				# new_question.form = form_for_question(new_question, magicform)
				# ajax_response = render_to_string(template_name, {
				# 				 'question_obj': new_question,
				# 				 'survey': magicform
				# 				})
				return HttpResponse("ajax_response")
	return HttpResponseRedirect(reverse('form_template_edit', kwargs={'form_id': magicform.id}))

@login_required 
@transaction.commit_on_success
def question_add(request,form_id):
	"""
	Params: form id
	
	Action: if the form has been submited checks that it is valid and
		creates a new field object. Checks if the question had choices,
		creates the necessary choice objects, assigns a field id to
		each of them and finally commits them to the database.
	
	Return: if method is ajax, returns ajax reponse else returns original view
	"""
	magicform = get_object_or_404(Survey, pk=form_id)
	if request.method == 'POST':
		question_choices = request.POST.getlist('qChoices')
		_qform = QuestionModelForm(request.POST, prefix="qn")
		if _qform.is_valid():
			new_question = _qform.save(commit=False) # save but don't commit yet, we need to add the template id
			new_question.survey = magicform
			new_question.save()
			if new_question.qtype in SELECT_FIELDS and question_choices:
				for choice_text in question_choices:
					choice_form = ChoiceForm({'text': choice_text})
					if choice_form.is_valid():
						new_choice = choice_form.save(commit=False)
						new_choice.question = new_question
						new_choice.save()
			if request.is_ajax():
				new_question.form = form_for_question(new_question, magicform)
				ajax_response = render_to_string('form_engine/field_list_item.html', {
								 'question_obj': new_question,
								 'survey': magicform
								})
				return HttpResponse(ajax_response)
	return HttpResponseRedirect(reverse('form_template_edit', kwargs={'form_id': magicform.id}))


@login_required
def view_main_page(request, template_name='form_engine/forms_home.html'):
	
	user_templates = Survey.author_manager.all_active(request.user)
	count_undeleted = user_templates.count()
	count_deleted = Survey.author_manager.num_deleted(request.user)
	count_filled = Survey.author_manager.all_filled(request.user)
	variables= RequestContext(request, {
				'request': request,
				'user_templates': user_templates,
				'count_filled': count_filled,
				'count_deleted': count_deleted,
				'count_undeleted': count_undeleted,
				})
	return render_to_response( template_name, variables)

@login_required
def view_form_entry(request,
					form_uuid= None,
					template_name='form_engine/view_entry.html',
					*args, **kwargs):
					
	user_form = Survey.objects.get(form_sessions__uuid=form_uuid)
	user_form.values = Answer.manager.user_form_values(request.user, form_uuid)
	count_undeleted = Survey.author_manager.num_active(request.user)
	count_deleted = Survey.author_manager.num_deleted(request.user)
	count_filled = Survey.author_manager.all_filled(request.user)
	variables = RequestContext(request, {
				'request': request,
				'user_form': user_form,
				'count_filled': count_filled,
				'count_deleted': count_deleted,
				'count_undeleted': count_undeleted,
				})
	return render_to_response( template_name, variables)

@login_required
def view_filled_forms(request, template_name='form_engine/view_entries.html'):
	
	user_sessions_list = FormSession.manager.user_sessions(request.user)
	count_undeleted = Survey.author_manager.num_active(request.user)
	count_deleted = Survey.author_manager.num_deleted(request.user)
	count_filled = Survey.author_manager.all_filled(request.user)
	variables= RequestContext(request, {
				'request': request,
				'user_sessions': user_sessions_list,
				'count_filled': count_filled,
				'count_deleted': count_deleted,
				'count_undeleted': count_undeleted,
				})
	return render_to_response( template_name, variables)

@login_required
def view_deleted_templates(request,
 			template_name='form_engine/deleted_templates.html',
			extra_context= None):
	
	my_deleted_templates = Survey.objects.filter(author=request.user, deleted=True)
	user_templates = Survey.objects.filter(author=request.user, deleted=False)
	count_undeleted = user_templates.count()
	count_deleted = Survey.objects.filter(author=request.user, deleted=True).count()
	variables= RequestContext(request, {
			'request': request,
			'my_deleted_templates': my_deleted_templates,
			'user_templates': user_templates,
			'count_deleted': count_deleted,
			'count_undeleted': count_undeleted,
		})
	return render_to_response(template_name, variables)


@login_required
def view_template_responses(request, 
			form_id, 
			template_name='form_engine/responses.html',
			extra_context= None):
	
	form_template = get_object_or_404(Survey, pk=form_id)
	form_fields = form_template.questions.filter(survey=form_id).order_by('order')
	#TODO: filter only the tempalates that have been completed and submitted
	form_sessions = FormSession.objects.filter(user=request.user)
	count_undeleted = Survey.author_manager.num_active(request.user)
	count_deleted = Survey.author_manager.num_deleted(request.user)
	count_filled = Survey.author_manager.all_filled(request.user)
	form_reponses = {}
	for session in form_sessions:
		answers = Answer.objects.filter(question__survey__id=form_template.id, form_session=session).order_by('question__order')
		if answers:
			form_reponses.update({session: answers})
	variables= RequestContext(request, {
			'request': request,
			'form_template': form_template,
			'form_fields': form_fields,
			'form_receipients': form_reponses,
			'count_filled': count_filled,
			'count_deleted': count_deleted,
			'count_undeleted': count_undeleted,
		})
	return render_to_response(template_name, variables)

@login_required
@transaction.commit_on_success
def create_form_template(request, 
			template_name='form_engine/new_template.html',
			extra_context= None):
			
	form = SurveyModelForm()
	if request.method == 'POST':
		#update the data base entry
		postdata = request.POST.copy()
		form = SurveyModelForm(postdata)
		if form.is_valid():
			new_template = form.save(commit=False)
			new_template.author = request.user
			new_template.save()
			return HttpResponseRedirect(reverse('form_template_edit',  kwargs={'form_id': new_template.id}))
			
	count_undeleted = Survey.author_manager.all_active(request.user).count()
	count_deleted = Survey.author_manager.num_deleted(request.user)
	count_filled = Survey.author_manager.all_filled(request.user)
	variables= RequestContext(request, {
			'request': request,
			'template_form': form,
			'count_filled': count_filled,
			'count_deleted': count_deleted,
			'count_undeleted': count_undeleted,
		})
	return render_to_response(template_name, variables)

@login_required
@transaction.commit_on_success
def copy_form_template(request,
 			form_id,
			template_name='form_engine/new_template.html',
			extra_context= None):
			
	form_template = get_object_or_404(Survey, pk=form_id)
	form_template.make_copy()
	return HttpResponseRedirect(reverse('forms_home'))
	
@login_required
@transaction.commit_on_success
def delete_form_template(request, form_id):

	target_template = get_object_or_404(Survey, pk=form_id)
	if target_template.author == request.user:
		target_template.deleted = True
		target_template.save()
	return HttpResponseRedirect(reverse('forms_home'))

@login_required
@transaction.commit_on_success
def restore_deleted_template(request, form_id):
	target_template = get_object_or_404(Survey, pk=form_id)
	if target_template:
		target_template.deleted = False
		target_template.save()
	return HttpResponseRedirect(reverse('my_deleted_templates'))

@login_required
def edit_form_template(request,
			form_id,
			template_name='form_engine/edit_template.html',
			extra_context= None):
		
	"""
	Displays page for creating or editing a form template
	"""
	form_template = get_object_or_404(Survey, pk=form_id)
	# if form_template.has_answers:
	# 	return HttpResponse("Template cannot be edited because it has data attached to it")
	form_template.update_form = SurveyModelForm(instance=form_template)
	item_forms = forms_for_survey_no_prefix(request, form_template)
	question_form = QuestionModelForm(prefix="qn")
	field_types = dict(QTYPE_CHOICES)
	variables= RequestContext(request, {
					'request': request,
					'form_template': form_template,
					'item_forms': item_forms,
					'question_form': question_form,
					'field_types': field_types,
		})
	return render_to_response(template_name,variables)

@login_required
def preview_form_template(request,
			form_id,
			template_name='form_engine/view_form.html',
			extra_context= None):
	"""
	Displays page with a form that can be filled out by any user
	Needs to check for user permissions
	"""
	form_template = get_object_or_404(Survey, pk=form_id)
	form_template.forms = forms_for_survey(request, form_template)
	variables= RequestContext(request, {
					'request': request,
					'user': request.user,
					'form_template': form_template,
		})
	return render_to_response(template_name, variables)
	
@login_required
@authorize_form
@transaction.commit_on_success
def process_submission(request,
 			form_slug,
			form_uuid=None,
			allow_edit_existing_answers=True,
			default_redirect='/',
			template_name='form_engine/view_form.html',):
	"""
	Displays survey to user for data entry
	if sessions are enabled, create a key based on the current form's id and
	retrive the session variable for it

	if this form already has a session key, them it probably has a suid.
	this will have to be removed eventually and instead an interview id will be used

	if form was submitted, verifies that all form fields are valid and save all data
	otherwise, generates the form. if the session uuid is availble, the form will be preloaded
	with previous answers. Otherwise, a fresh from is generated
	"""
	form_template = get_object_or_404(Survey, slug=form_slug)
	user_session = None
	skey = 'form_%d' % form_template.id
	suid = '%s_uuid' % skey
	if form_uuid == None:
		form_uuid = request.session.get(suid, False) or uuid.uuid4().hex
	if hasattr(request, 'session') and request.method == 'GET':
		request.session[skey]= (request.session.get(skey, False) or request.method == 'POST')
		request.session[suid] = form_uuid
		request.session.modified = True
	try:
		user_session = FormSession.objects.get(uuid=form_uuid)
	except ObjectDoesNotExist:
		user_session = FormSession.manager.create_form_session(request.user, form_template, form_uuid)
	forms_collection = forms_for_survey(request, form_template, user_session)
	if request.method == 'POST':
		if all(form.is_valid() for form in forms_collection):
			for form in forms_collection:
				form.save()
			# since the form has valid data marked, mark the current user session as complete	
			user_session.complete = True
			user_session.complete_date = datetime.now()
			user_session.save()
			# delete the current session information 
			request.session[suid] = None
			request.session.modified = True # enforce the cookie save.
			#redirect to the form completion page
			redirect_url = request.POST.get('next', default_redirect or reverse('forms_home'))
			
			return HttpResponseRedirect("%s?next=%s" % (reverse('form_success_page'), redirect_url))
		print [form.errors for form in forms_collection]
	redirect_url = request.GET.get('next' or default_redirect)
	variables = RequestContext(request, {
							'request': request,
							'form_template': form_template,
							'forms_collection':forms_collection,
							'next': redirect_url,
				})
	return render_to_response(template_name,variables)

def submission_success(request,
 					default_redirect='/',
					template_name='form_engine/success.html'):
	success_redirect = request.GET.get('next' or default_redirect)
	variables = RequestContext(request, {
				'success_redirect_url': success_redirect,
			})
	return render_to_response(template_name, variables)

@login_required
@transaction.commit_on_success
def edit_survey_settings(request, form_id,
							template_name='form_engine/settings.html'):
	form_template = get_object_or_404(Survey, id=form_id)
	item_forms = forms_for_survey_no_prefix(request, form_template)
	#create a new update form
	settings_form = SurveyModelForm(request.POST or None, instance=form_template)
	if settings_form.is_valid():
		settings_form.save()
	variables = RequestContext(request, {
							'request': request,
							'form_template': form_template,
							'item_forms': item_forms,
							'settings_form': settings_form,
							})
	#ajax request return ajax response
	if request.is_ajax:
		ajax_response = render_to_string(template_name, variables)
		#non-ajax request takes user to a new page
	return render_to_response(template_name, variables)	