#! /usr/bin/env python
# -*- coding: utf-8 -*-


# OpenFisca -- A versatile microsimulation software
# By: OpenFisca Team <contact@openfisca.fr>
#
# Copyright (C) 2011, 2012, 2013, 2014, 2015 OpenFisca Team
# https://github.com/openfisca
#
# This file is part of OpenFisca.
#
# OpenFisca is free software; you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# OpenFisca is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import codecs
import collections
import json
import re

import logging
from pandas import HDFStore
import yaml


# import pandas.rpy.common as com     # need to import it just for people using Rdata files
# import rpy2.rpy_classic as rpy
#
#
# rpy.set_default_mode(rpy.NO_CONVERSION)

ident_re = re.compile(u"(?i)ident\d{2,4}$")


log = logging.getLogger(__name__)


class Survey(object):
    """
    An object to describe survey data
    """
    hdf5_file_path = None
    label = None
    name = None
    tables = None
    tables_index = dict()
    informations = dict()

    def __init__(self, name = None, label = None, hdf5_file_path = None, **kwargs):
        assert name is not None, "A survey should have a name"
        self.name = name
        self.tables = dict()  # TODO: rework to better organize this dict

        if label is not None:
            self.label = label

        if hdf5_file_path is not None:
            self.hdf5_file_path = hdf5_file_path

        self.informations = kwargs

    def __repr__(self):
        header = """{} : survey data {}
Contains the following tables : \n""".format(self.name, self.label)
        tables = yaml.safe_dump(self.tables.keys(), default_flow_style = False)
        informations = yaml.safe_dump(self.informations, default_flow_style = False)
        return header + tables + informations

    @classmethod
    def create_from_json(cls, survey_json):
        self = cls(
            name = survey_json.get('name'),
            label = survey_json.get('label'),
            hdf5_file_path = survey_json.get('hdf5_file_path'),
            **survey_json.get('informations')
            )
        self.tables = survey_json.get('tables')
        return self

    def dump(self, file_path):
        with codecs.open(file_path, 'w', encoding = 'utf-8') as _file:
            json.dump(self.to_json(), _file, encoding = "utf-8", ensure_ascii = False, indent = 2)

    def find_tables(self, variable = None, tables = None):
        container_tables = []
        assert variable is not None
        if tables is None:
            tables = self.tables
        tables_index = self.tables_index
        for table in tables:
            if table not in tables_index.keys():
                tables_index[table] = self.get_columns(table)
            if variable in tables_index[table]:
                container_tables.append(table)
        return container_tables

    def get_columns(self, table = None):
        assert table is not None
        store = HDFStore(self.hdf5_file_path)
        assert table in store
        log.info("Building columns index for table {}".format(table))
        return list(store[table].columns)

    def get_value(self, variable = None, table = None):
        """
        Get value

        Parameters
        ----------
        variable : string
                  name of the variable
        table : string, default None
                name of the table hosting the variable
        Returns
        -------
        df : DataFrame, default None
             A DataFrame containing the variable
        """
        assert variable is not None, "A variable is needed"
        if table not in self.tables:
            log.error("Table {} is not found in survey tables".format(table))
        df = self.get_values([variable], table)
        return df

    def get_values(self, variables = None, table = None, lowercase = True, rename_ident = True):
        """
        Get values

        Parameters
        ----------
        variables : list of strings, default None
                  list of variables names, if None return the whole table
        table : string, default None
                name of the table hosting the variables
        lowercase : boolean, deflault True
                    put variables of the table into lowercase
        rename_ident :  boolean, deflault True
                        rename variables ident+yr (e.g. ident08) into ident
        Returns
        -------
        df : DataFrame, default None
             A DataFrame containing the variables
        """
        store = HDFStore(self.hdf5_file_path)
        try:
            df = store[table]
        except KeyError:
            df = store[self.tables[table]["Rdata_table"]]

        if lowercase is True:
            columns = dict((column_name, column_name.lower()) for column_name in df)
            df.rename(columns = columns, inplace = True)

        if rename_ident is True:
            for column_name in df:
                if ident_re.match(column_name) is not None:
                    df.rename(columns = {column_name: "ident"}, inplace = True)
                    log.info("{} column have been replaced by ident".format(column_name))
                    break

        if variables is None:
            return df
        else:
            diff = set(variables) - set(df.columns)
            if diff:
                raise Exception("The following variable(s) {} are missing".format(diff))
            variables = list(set(variables).intersection(df.columns))
            df = df[variables]
            return df

    def insert_table(self, name = None, **kwargs):
        """
        Insert a table in the Survey object
        """
        if name not in self.tables:
            self.tables[name] = dict()
        for key, val in kwargs.iteritems():
            self.tables[name][key] = val

    @classmethod
    def load(cls, file_path):
        with open(file_path, 'r') as _file:
            self_json = json.load(_file)
        log.info("Getting survey information for {}".format(self_json.get('name')))
        self = cls.create_from_json(self_json)
        return self

    def to_json(self):
        self_json = collections.OrderedDict((
            ))
        self_json['hdf5_file_path'] = self.hdf5_file_path
        self_json['label'] = self.label
        self_json['name'] = self.name
        self_json['tables'] = collections.OrderedDict(sorted(self.tables.iteritems()))
        self_json['informations'] = collections.OrderedDict(sorted(self.informations.iteritems()))
        return self_json
