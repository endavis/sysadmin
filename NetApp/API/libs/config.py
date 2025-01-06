"""
# return any items match all 3 tags
-f '{"bu":"Business", "env":"Prod", "tags":"active"}'
# return any item that matches bu and env and has both 'active' and 'workload' as a tag
-f '{"bu":"Business", "env":"Prod", "tags":"active && workload"}'
# return any item that matches bu, env, and tags and is app is one of app_name1 or app_name2
-f '{"bu":"Business", "app": "app_name1 || app_name2", "env":"Prod", "tags":"active"}'
# return any items with either name1 or name2
-f '{"name":"name1 || name2"}'

a data toml has the following section:
[settings]
type='data'

the following sections are valid in a data toml:
[aiquims]
[connectors]
[clusters]
[cloudinsights]
[azure]
[ibm]

This data is loaded into the Config.data attribute

And there are several ways to group this data into tomls:
1) A specific toml for each type of data
2) a toml for each distinct unit, like division, or bu

In addition, there are specific tomls
Azure settings (azure.toml)
IBM/Softlayer settings (ibm.toml)
AWS settings (aws.toml)
global settings (settings.toml)

These tomls are loading into the Config.config attribute by file name (without the .toml)
"""
import tomllib
import logging
import pprint
import pathlib
from .log import setup_logger

config_logger = setup_logger('toml-data')

class Config:
    def __init__(self, data_dir, debug=False):
        self.data = {}
        self.data_dir = pathlib.Path.cwd() / data_dir
        self.data_types = ['aiqums', 'connectors', 'cloudinsights', 'clusters', 'azure']
        self.settings = {}
        if debug:
            config_logger.setLevel(logging.DEBUG)
            config_logger.debug('toml-config: setting logging to debug')
        self.parse_data()

    def parse_data(self):

        all_tomls = self.data_dir.rglob('*.toml')
        loaded_tomls = []
        for file in all_tomls:
            config_logger.debug(f"parsing {file}")
            self.parse_toml(file)
            loaded_tomls.append(file.stem)

        config_logger.debug(f"loaded the following files: {', '.join(loaded_tomls)}")
        print(f"loaded the following files: {', '.join(loaded_tomls)}")        
        self.add_searchable_keys()

    def parse_toml(self, file):
        with open(file, "rb") as f:
            data = tomllib.load(f)
            if 'settings' in data and 'type' in data['settings'] and data['settings']['type'] == 'data':
                print(f'data file: {file.stem}')
                self.load_data(data)
            else: 
                print(f'config file: {file.stem}')
                if file.stem not in self.settings:
                    self.settings[file.stem] = data
                else:
                    self.settings[file.stem].update(data)

    def count(self, section, id='name'):
        found = []
        for item in self.data[section]:
            try:
                found.append(getattr(item, id))
            except AttributeError:
                found.append(self.data[section][item][id])
        return len(set(found))

    def add_searchable_keys(self):
        for data_type in self.data_types:
            if data_type in self.settings['settings'] and  'searchable_keys' in self.settings['settings'][data_type]:
                default_keys = self.settings['settings'][data_type]['searchable_keys']
                for item in self.data[data_type]:
                    if 'name' not in self.data[data_type][item]:
                        self.data[data_type][item]['name'] = item
                    for key in default_keys:
                        if key not in self.data[data_type][item]:
                            self.data[data_type][item][key] = ''        

    def load_data(self, data):
        for data_type in self.data_types:
            if data_type not in self.data:
                self.data[data_type] = {}
            if data_type in data:
                self.data[data_type].update(data[data_type])

    def chk_and(self, search_term, values):
        """
        >>> chk_and(test, 'active && Document', ['active'])
        ['active', 'Document']
        False
        >>> chk_and(test, 'active && Document', ['active', 'Document'])
        ['active', 'Document']
        True
        >>> chk_and(test, 'active && Document && Tax', ['active', 'Document'])
        ['active', 'Document', 'Tax']
        False
        >>> chk_and(test, 'Document && active', ['active', 'Document'])
        ['Document', 'active']
        """
        # && only makes sense for lists
        if not isinstance(values, list):
            return False
        terms = [item.strip() for item in search_term.split(' && ')]
        return set(terms).issubset(values)

    def chk_or(self, search_term, value):
        """
        >>> chk_or(test, 'active || Document', ['active'])
        True
        >>> chk_or(test, 'Tax || Document', ['active'])
        False
        >>> chk_or(test, 'Tax || Document || active', ['active'])
        True
        >>> chk_or(test, 'Document || active', ['active', 'Tax'])
        True
        >>> chk_or(test, 'Document || Test', ['active', 'Tax'])
        """
        terms = [item.strip() for item in search_term.split(' || ')]
        if isinstance(value, list):
            return any(item in value for item in terms)
        else:
            return any(item == value for item in terms)

    def check_term(self, term, value):
        if ' || ' in term:
            return self.chk_or(term, value)
        elif ' && ' in term:
            return self.chk_and(term, value)
        else:
            if isinstance(value, list):
                return term in value
            else:
                return term == value

    def search(self, data_type, search_dict):
        """
        search for items that match the given fields
        each param should be a dictionary with field and value

        this is case insensitive

        value can be {'tags':'active && Document'} or
                     {'app': 'Axcess || ELF'}

        {
        'div' : 'TAA',
        'bu' : 'Professional',
        'app' : 'Axcess'
        }
        """
        if not search_dict:
            return self.data[data_type].copy()

        results = {}
        for item in self.data[data_type]:
            item_details = self.data[data_type][item]
            result_check = []
            for key in search_dict:
                if key not in item_details:
                    result_check.append(False)
                    break
                result_check.append(self.check_term(search_dict[key], item_details[key]))

            if all(result_check):
                results[item] = item_details

        return results

    def get_clusters(self, search_terms):
        return self.search('clusters', search_terms)

    def find_closest(self, data_type: str, tree: dict):
        tree = tree.copy()
        key_order = ['div', 'bu', 'app', 'env', 'subapp', 'cloud', 'region']
        key_order.reverse()
        found = None

        # remove empty keys
        for key in key_order:
            if tree[key] == "":
                del tree[key]

        config_logger.debug(f"  initial search {tree = }")
        # try matching tree as is
        results = self.search(data_type, tree)
        if len(results) == 1:
            found = results.popitem()[1]

        else:
            # go through the key_order and delete keys until something is found
            for key in key_order:
                if key in tree:
                    config_logger.debug(f"  removing {key} and searching {tree = }")
                    del tree[key]
                else:
                    continue
                if tree:
                    results = self.search(data_type, tree)
                    config_logger.debug(f"  search_returned {results}")
                    if len(results) == 1:
                        found = results.popitem()[1]
                        break

        config_logger.debug(f"  {found = }")
        return found
