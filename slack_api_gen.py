'''
slack_api_gen.py
Auto-generate st2 action meta yamls by scraping api.slack.com

Usage: python slack_api_gen.py

Make sure to have following packages in place to use this script.

- pyyaml
- bs4
- html5lib
'''

import yaml
import re
import urllib2
from bs4 import BeautifulSoup

# Use OrderedDict to keep params order listed in API web page
from collections import OrderedDict


# pyyaml representer method for OrderedDict
def represent_odict(dumper, instance):
    return dumper.represent_mapping('tag:yaml.org,2002:map', instance.items())


yaml.SafeDumper.add_representer(OrderedDict, represent_odict)


# For fields that should be double-quoted in resulting yaml should use this
# str wrapper class
class doublequoted_string(str):
    pass


# pyyaml representer method for doublequoted_string class defined above
def doublequoted_string_representer(dumper, data):
    return dumper.represent_scalar(u'tag:yaml.org,2002:str', data, style='"')


yaml.SafeDumper.add_representer(
    doublequoted_string, doublequoted_string_representer)

method_dict = {}
base_url = 'https://api.slack.com/methods'

api_doc_main = urllib2.urlopen('%s/channels.invite' % base_url)

soup = BeautifulSoup(api_doc_main, 'html5lib')

api_methods = soup.find('select', id='api_method')

for method in api_methods.stripped_strings:
    if method != 'View another method...':
        method_dict[method] = {'params': OrderedDict()}
        method_url = "%s/%s" % (base_url, method)
        method_page = urllib2.urlopen(method_url)
        method_soup = BeautifulSoup(method_page, 'html5lib')
        method_description = method_soup.find('section', attrs={
            "class": "tab_pane selected clearfix large_bottom_padding"}) \
            .find_all('p')[0].text
        method_description = re.sub('\n|\r', ' ', method_description)
        method_dict[method]['description'] = method_description
        method_args_table = method_soup.find('table', attrs={
            "class": "arguments full_width"}).tbody.find_all('tr')
        del method_args_table[0]
        for row in method_args_table:
            arg = row.find('code')
            required = row.find_all('td')[2]
            if re.search("Required", required.text):
                required = True
                default = None
            elif re.search(",", required.text):
                required, default = required.text.split(',')
                required = False
                default = default.split('=')[1]
            else:
                required = False
                default = None
            method_dict[method]['params'][arg.text] = {}
            method_dict[method]['params'][arg.text]['required'] = required
            method_dict[method]['params'][arg.text]['default'] = default

for method in method_dict:

    file_name = 'actions/%s.yaml' % method
    output_dict = {
        'name': method,
        'runner_type': 'python-script',
        'enabled': True,
        'entry_point': 'run.py',
        'description': doublequoted_string(method_dict[method]['description']),
        'parameters': OrderedDict()}
    output_dict['parameters']['end_point'] = {
        'type': 'string',
        'immutable': True,
        'default': method}

    for param in method_dict[method]['params']:
        if param == 'token':
            method_dict[method]['params'][param]['required'] = False
        output_dict['parameters'][param] = OrderedDict()
        output_dict['parameters'][param]['required'] = \
            method_dict[method]['params'][param]['required']
        if method_dict[method]['params'][param]['default'] is not None:
            output_dict['parameters'][param]['default'] = \
                doublequoted_string(
                    method_dict[method]['params'][param]['default'])
        output_dict['parameters'][param]['type'] = 'string'

    print yaml.safe_dump(
        output_dict, default_flow_style=False, width=float('inf'))
    fh = open(file_name, 'w')
    fh.write(yaml.safe_dump(
        output_dict, default_flow_style=False, width=float('inf')))
    fh.close()
