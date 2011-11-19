from apps.form_engine.models import *
from django import template

register = template.Library()

@register.filter(name='undeleted_forms')
def num_undeleted_forms(user):
	return Survey.author_manager.num_undeleted(user) 
	
@register.filter(name='deleted_forms')
def num_deleted_forms(user):
	return	Survey.author_manager.num_deleted(user)	
			
@register.filter(name='filled_forms')
def num_filled_forms(user):
	return	Survey.author_manager.all_filled(user)
	
@register.filter(name='form_templates')
def num_active_forms(user):
	return	Survey.author_manager.num_active(user)

@register.filter(name='public_templates')
def num_public_forms(user):
	return	Survey.author_manager.all_public().count()

def forms_side_panel(user):
	pass
	# <span class="app-title">Forms</span>
	# <ul>
	# 	{% url manage_my_forms as panel_link %}
	# 	<li class="menu-links panel {% active request panel_link %}"><a href="{% url manage_my_forms %}">My forms ({{ count_undeleted|default_if_none:0 }})</a></li>
	# 	{% url my_filled_forms as panel_link %}
	# 	<li class="menu-links panel {% active request panel_link %}"><a href="{% url my_filled_forms %}">My entries ({{ count_filled|default_if_none:0 }})</a></li>
	# 	{% url form_template_create as panel_link %}
	# 	<li class="menu-links panel {% active request panel_link %}"><a href="{% url form_template_create %}">New form</a></li>
	# 	<li class="menu-links panel"><a href="">Import form</a></li>
	# 	{% url my_deleted_templates as panel_link %}
	# 	<li class="menu-links panel {% active request panel_link %}"><a href="{% url my_deleted_templates %}">Trash ({{ count_deleted|default_if_none:0 }})</a></li>
	# </ul>
