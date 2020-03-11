import pathlib
import json
import zipfile
import re

from collections import OrderedDict
from cldfbench import Dataset as BaseDataset


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "sndcmpvanuatu"

    data_file_name = 'vanuatu.json'
    catalog_file_name = 'catalog.json'

    def cldf_specs(self):  # A dataset must declare all CLDF sets it creates.
        return super().cldf_specs()

    def cmd_download(self, args):
        # download raw JSON data from https://soundcomparisons.com into folder /raw
        self.raw_dir.download(
            'https://soundcomparisons.com/query/data?study=Vanuatu',
            self.data_file_name)

        # Get all FilePathParts from Languages
        json_data = self.raw_dir.read_json(self.data_file_name)
        language_FilePathParts = [l['FilePathPart']
                                  for l in json_data["languages"]]

        # download raw sound file catalog as JSON data
        with self.raw_dir.temp_download(
                'https://github.com/clld/soundcomparisons-data/raw/master/soundfiles/catalog.json.zip',
                '_cat_temp.json.zip') as p:
            with zipfile.ZipFile(p, 'r') as z:
                for filename in z.namelist():
                    with z.open(filename) as f:
                        json_cat = json.loads(
                            f.read().decode('utf-8'), encoding='utf-8')
                    break

        # Prune catalog to used sound files only
        catalog = {json_cat[oid]['metadata']['name']: dict(**json_cat[oid], id=oid)
                   for oid in json_cat
                   if re.split(r'_\d+_', json_cat[oid]['metadata']['name'])[0]
                   in language_FilePathParts}
        with open(self.raw_dir / self.catalog_file_name, 'w', encoding='utf-8') as f:
            json.dump(OrderedDict(sorted(catalog.items())),
                      f, ensure_ascii=False, indent=1)


    def cmd_makecldf(self, args):
        """
        Convert the raw data to a CLDF dataset.

        >>> args.writer.objects['LanguageTable'].append(...)
        """
