from functools import wraps
from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render_to_response
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse, Http404
from apps.form_engine.forms import Survey
from apps.form_engine.forms import *

def authorize_form(func): 
	@wraps(func)   
	def decorator(request,*args, **kwargs):
		form_slug = kwargs.get('form_slug')
		form_template = get_object_or_404(Survey, slug=form_slug)
		# if magicform.closed:
		# 	pass
	        # if magicform.answers_viewable_by(request.user):
	        #     return HttpResponseRedirect(reverse('survey-results', None, (),
	        #                                         {'survey_slug': survey_slug}))
		# if user has a session and have answered some questions
	    # and the survey does not accept multiple answers,
	    # go ahead and redirect to the answers, or a thank you
		# if (hasattr(request, 'session') and
		# 			magicform.has_answers_from(request.session.session_key) and
		# 			not magicform.allows_multiple_interviews and not allow_edit_existing_answers):
		# 	return _survey_redirect(request, survey,group_slug=group_slug)

		# if the survey is restricted to authentified user redirect anonymous user to the login page
		if form_template.restricted and str(request.user) == "AnonymousUser":
			return HttpResponseRedirect(reverse("login")+"?next=%s" % request.path)
		# if cookies are not enabeled, notify user
		if request.method == 'POST' and not hasattr(request, 'session'):
			return HttpResponse(unicode(_('Cookies must be enabled.')), status=403)
		return func(request, *args, **kwargs)
	return decorator
