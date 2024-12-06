"""
# the below will check each item
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":"tag1"}'
# the below will check if a tag matches one of the tags in the list
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":["tag1", "tag2"]}'
# the below will only return items that have both tags
-f '{"div":"div1"}' '{"bu":"bu1"}' '{"tags":"tag1"} '{"tags":"tag2"}'

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

    def search(self, data_type, search_terms):
        """
        search for items that match the given fields
        each param should be a dictionary with field and value

        this is case insensitive
        """
        config_logger.debug(f"{search_terms = }")
        if not search_terms:
            data_copy = self.data[data_type].copy()
            if 'settings' in data_copy:
                del(data_copy['settings'])
            return data_copy
        results = {}
        for item in self.data[data_type]:
            if item == 'settings':
                continue
            item_details = self.data[data_type][item]
            config_logger.debug(f"{item_details = }")
            result_check = []
            for term in search_terms:
                config_logger.debug(f"{term = }")
                for search_field,search_value in term.items():
                    config_logger.debug(f"{search_field = } {search_value = }")
                    if isinstance(item_details[search_field.lower()], list):
                        if isinstance(v, list):
                            found = False
                            for i in search_value:
                                if i in item_details[search_field.lower()]:
                                    found = True
                            config_logger.debug(f"checking list in list: {found}")
                            result_check.append(found)
                            continue
                        else:
                            if search_value in item_details[search_field.lower()]:
                                config_logger.debug('item_details[search_field.lower()] is a list and search_value is in it')
                                result_check.append(True)
                                continue
                    else:
                        if isinstance(search_value, list):
                            if item_details[search_field.lower()].lower() in search_value:
                                config_logger.debug('search_value == item_details[search_field.lower()]')
                                result_check.append(True)
                                continue
                            if item_details[search_field.lower()] in search_value:
                                config_logger.debug('search_Value in item_details[search_field.lower()]')
                                result_check.append(True)
                                continue
                        else:
                            if search_value == item_details[search_field.lower()].lower():
                                config_logger.debug('search_value == item_details[search_field.lower()]')
                                result_check.append(True)
                                continue
                            if search_value in item_details[search_field.lower()]:
                                config_logger.debug('search_Value in item_details[search_field.lower()]')
                                result_check.append(True)
                                continue
                    config_logger.debug("unsuccessful")
                    result_check.append(False)

            if all(result_check):
                results[item] = item_details
        return results

    def get_clusters(self, search_terms):
        return self.search('clusters', search_terms)

    def get_utilities(self, data_type, search_terms, ignore=None):
        search_result = self.search(data_type, search_terms)
        config_logger.debug(f"match_exact {data_type = } {search_terms = }")
        keys_to_ignore = ['name', 'url', 'ip']
        if ignore:
            keys_to_ignore.extend(ignore)
        search_terms_to_remove = []
        for i, search_item in enumerate(search_terms):
            for key in keys_to_ignore:
                if key in search_item:
                    search_terms_to_remove.append(search_item)
        for item in search_terms_to_remove:
            search_terms.remove(item)
        search_result = self.search(data_type, search_terms)
        found = []
        for item in search_result:
            config_logger.debug(f"  {item =}")
            data_keys = list(self.data[data_type][item].keys())

            # ignore keys that are not ints or strings
            for key in data_keys:
                if not isinstance(self.data[data_type][item][key], (str, int)):
                    try:
                        data_keys.remove(key)
                    except ValueError:
                        pass

            # remove keys that should be ignored
            for key in keys_to_ignore:
                try:
                    data_keys.remove(key)
                except ValueError:
                    pass

            config_logger.debug(f"  keys left to check: {data_keys}")

            new_key_list = data_keys[:]
            for key_to_check in data_keys:
                if key_to_check not in self.data[data_type][item]:
                    new_key_list.remove(key_to_check)
                if self.data[data_type][item][key_to_check] in ['', None]:
                    new_key_list.remove(key_to_check)
            
            for key_to_check in search_terms:
                config_logger.debug(f"  {key_to_check}")
                for key2 in key_to_check:
                    if key2 in new_key_list:
                        new_key_list.remove(key2)

            if len(new_key_list) == 0:
                found.append(self.data[data_type][item])
                config_logger.debug(f"  match {item = }")
            else:
                config_logger.debug(f"  {new_key_list = }", stack_info=True)
                
        config_logger.debug(f"{found = }")
        return found
            

