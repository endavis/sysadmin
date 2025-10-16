"""
# return any items match all 3 tags
-f '{"bu":"Business", "env":"Prod", "tags":"active"}'
# return any item that matches bu and env and has both 'active' and 'workload' as a tag
-f '{"bu":"Business", "env":"Prod", "tags":"active && workload"}'
# return any item that matches bu, env, and tags and app is one of app_name1 or app_name2
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
import sys
import os

file_name = pathlib.Path(__file__).name

class Config:
    def __init__(self, config_dir, output_dir, args=None):
        self.data = {}
        self.args = args
        self.config_dir = pathlib.Path.cwd() / config_dir
        self.data_types = ['aiqums', 'connectors', 'cloudinsights', 'clusters', 'azure']
        self.settings = {}
        self.parse_data()
        self.script_name = pathlib.Path(sys.argv[0]).stem
        self.output_dir = pathlib.Path(os.getcwd()) / output_dir
        self.db_dir = self.output_dir / 'db'
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)

    def get_schema_location(self, api_name):
        return pathlib.Path(self.config_dir / "apis" / api_name)

    def parse_data(self):
        all_tomls = self.config_dir.rglob('*.toml')
        loaded_tomls = []
        for file in all_tomls:
            logging.debug(f"{file_name} : parsing {file}")
            self.parse_toml(file)
            loaded_tomls.append(file.stem)

        logging.debug(f"{file_name} :loaded the following files: {', '.join(loaded_tomls)}")
        self.add_searchable_keys()

    def parse_toml(self, file):
        with open(file, "rb") as f:
            data = tomllib.load(f)
            if 'settings' in data and 'type' in data['settings'] and data['settings']['type'] == 'data':
                logging.debug(f"{file_name} : data file: {file.stem}")
                self.load_data(data)
            else:
                logging.debug(f"{file_name} : config file: {file.stem}")
                if file.stem not in self.settings:
                    self.settings[file.stem] = data
                else:
                    self.settings[file.stem].update(data)

    def get_user(self, utype="clusters", uobject=""):
        user = None
        enc = None

        try:
            user = self.settings['users'][utype]['user']
            enc = self.settings['users'][utype]['enc']
        except KeyError:
            pass

        try:
            user = self.data[utype][uobject]['user']
            enc = self.data[utype][uobject]['enc']
        except KeyError:
            pass

        if not user:
            logging.error(f"Could not find user for {utype} and {uobject}")
            sys.exit(1)
        if not enc:
            logging.error(f"Could not find password for {utype} and {uobject}")
            sys.exit(1)

        return user, enc


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
                logging.debug(f"{file_name} : adding {len(data[data_type])} {data_type} items")
                self.data[data_type].update(data[data_type])

    def chk_and(self, search_term, values):
        """
        >>> chk_and(test, 'active && workload1', ['active'])
        ['active', 'workload1']
        False
        >>> chk_and(test, 'active && workload1', ['active', 'workload1'])
        ['active', 'workload1']
        True
        >>> chk_and(test, 'active && workload1 && workload2', ['active', 'workload1'])
        ['active', 'workload1', 'workload2']
        False
        >>> chk_and(test, 'workload1 && active', ['active', 'workload1'])
        ['workload1', 'active']
        """
        # && only makes sense for lists
        if not isinstance(values, list):
            return False
        terms = [item.strip() for item in search_term.split(' && ')]
        return set(terms).issubset(values)

    def chk_or(self, search_term, value):
        """
        >>> chk_or(test, 'active || workload1', ['active'])
        True
        >>> chk_or(test, 'workload1 || workload2', ['active'])
        False
        >>> chk_or(test, 'workload1 || workload2 || active', ['active'])
        True
        >>> chk_or(test, 'workload1 || active', ['active', 'workload2'])
        True
        >>> chk_or(test, 'workload1 || Test', ['active', 'workload2'])
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

        value can be {'tags':'active && Workload'} or
                     {'app': 'App1 || App2'}

        """
        if not search_dict:
            return self.data[data_type].copy()
        logging.debug(f"{file_name} :    search:")
        logging.debug(f"{file_name} :     {data_type = }")
        logging.debug(f"{file_name} :     {search_dict = }")
        results = {}
        for item in self.data[data_type]:
            item_details = self.data[data_type][item]
            logging.debug(f"{file_name} :      search: item - {item_details['name']}")
            result_check = []
            for key in search_dict:
                logging.debug(f"{file_name} :      search: checking {key}")
                if key not in item_details:
                    result_check.append(False)
                    logging.debug(f"{file_name} :      search: {key} not in item details, did not match")
                    break
                logging.debug(f"{file_name} :      search: check_term {search_dict[key]}, {item_details[key]} returned {self.check_term(search_dict[key], item_details[key])}")
                result_check.append(self.check_term(search_dict[key], item_details[key]))

            if all(result_check):
                logging.debug(f"{file_name} :      search: item - {item_details['name']} matched")
                results[item] = item_details
            else:
                logging.debug(f"{file_name} :      search: item - {item_details['name']} did not match")

        logging.debug(f"{file_name} : search - {results = }")
        return results

    def get_clusters(self, search_terms):
        return self.search('clusters', search_terms)

    def find_closest(self, data_type: str, tree: dict):
        logging.debug(f"{file_name} :find_closest")
        logging.debug(f"{file_name} :  {data_type = }")
        logging.debug(f"{file_name} :  {tree = }")
        tree = tree.copy()
        key_order = ['div', 'bu', 'app', 'env', 'subapp', 'cloud', 'region']
        key_order.reverse()
        found = None

        # remove empty keys
        for key in key_order:
            if tree[key] == "":
                del tree[key]

        logging.debug(f"{file_name} :  initial search {tree = }")
        # try matching tree as is
        results = self.search(data_type, tree)
        if len(results) == 1:
            found = results.popitem()[1]

        else:
            # go through the key_order and delete keys until something is found
            for key in key_order:
                if key in tree:
                    logging.debug(f"{file_name} :  removing {key} and searching {tree = }")
                    del tree[key]
                else:
                    continue
                if tree:
                    results = self.search(data_type, tree)
                    logging.debug(f"{file_name} :  search_returned {results}")
                    if len(results) == 1:
                        found = results.popitem()[1]
                        break

        logging.debug(f"{file_name} : find_closest - {found = }")
        return found
