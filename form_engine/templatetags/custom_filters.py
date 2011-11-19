import re
from django import template

register = template.Library()

@register.simple_tag
def active(request, pattern):
	if re.search(pattern, request.path):
		return 'active'
	return ''
	
@register.filter(name='tablecols')
def tablecols(data, cols):
	rows = []
	row = []
	index = 0
	for user in data:
		row.append(user)
		index = index + 1
		if index % cols == 0:
			rows.append(row)
			row = []
	# Still stuff missing?
	if len(row) > 0:
		rows.append(row)
	return rows
	
@register.filter(name='objectAtIndex')
def tablecols(array, index):
	if type(index) != int:
		raise template.TemplateSyntaxError("objectAtIndex takes an integer as it's second argument")
	print list(array)
	print index
	if type(list(array)) != list:
		raise template.TemplateSyntaxError("objectAtIndex takes an array as it's first argument")
	try:
		return array[index]
	except:
		return None
