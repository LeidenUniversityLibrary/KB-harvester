from kb.nl.api import sru
from kb.nl.api.sru import response
import urllib


class Response(response):
    def __iter__(self):
        return self

    def next(self):
        if self.sru.nr_of_records == 0:
            raise StopIteration
        elif self.sru.startrecord < self.sru.nr_of_records:
            record_data = self.sru.run_query()
            self.sru.startrecord += self.sru.maximumrecords
            return Response(record_data, self.sru)
        else:
            raise StopIteration


class Sru():

    def __init__(self):
        self.sru = sru

        self.sru.sru_collections.update({'DDD': {'collection': 'DDD_krantnr',
                'description_en': 'Historical Newspapers',
                'description_nl': 'Historische Kranten',
                'metadataPrefix': 'didl',
                'recordschema': 'ddd',
                'setname': 'DDD',
                'time_period': [1883, 1976]}})

    def search(self, query, collection=False,
               startrecord=1, maximumrecords=1, recordschema=False):

        self.sru.maximumrecords = maximumrecords
        self.sru.query = urllib.quote_plus(query)
        self.sru.startrecord = startrecord

        if collection not in self.sru.sru_collections:
            raise Exception('Unknown collection')

        self.sru.collection = self.sru.sru_collections[collection]['collection']

        if not self.sru.collection:
            raise Exception('Error, no collection specified')

        if not recordschema:
            self.sru.recordschema = self.sru.sru_collections[collection]['recordschema']
        else:
            self.sru.recordschema = recordschema

        query_result = self.sru.run_query()

        nr_of_records = query_result.find("{http://www.loc.gov/zing/srw/}numberOfRecords").text

        self.sru.nr_of_records = int(nr_of_records)

        if nr_of_records > 0:
            return Response(query_result, self.sru)

        return False
