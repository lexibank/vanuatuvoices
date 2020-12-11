"""
Download audio files.

Will create/use a directory structure
- audio
  |- <concept-ID>
     |- <media-IA>.<suffix>

If --create-release is passed it'll create a directory {id}_audio
containing audio.zip, zenodo.json, and README.md for releasing on Zenodo

If --update-zenodo ID is passed it'll update the Zenodo deposit ID's metadata
with the content of {id}_audio/zenodo.json.
"""
import time
import pathlib
import threading
import collections
import os
import zipfile
import html
import warnings
import requests

import zenodoclient
from zenodoclient.api import Zenodo, API_URL, ACCESS_TOKEN

from urllib.request import urlretrieve

from clldutils import jsonlib
from clldutils.path import md5
from clldutils.misc import format_size
from clldutils.clilib import PathType
from clldutils.jsonlib import update
from cldfbench.metadata import get_creators_and_contributors
from cldfbench.datadir import DataDir

import tqdm
from pycldf import Dataset

from lexibank_vanuatuvoices import Dataset

GITHUB_PREFIX = 'https://github.com/lexibank/'

RELEASE_NOTE = """## {0}

This dataset contains the WAV audio files of the project [{3}]({1}{2})
as zip-archived folder *audio*.

The audio files are structured into separate folders named by the internal used
[parameter IDs]({1}{2}/blob/master/cldf/parameters.csv).
Each individual audio file is named according to the ID specified in the file
[media.csv]({1}{2}/blob/master/cldf/media.csv).

{4}
"""

LISENCE = "This dataset is licensed under {0}."

VERSION = "1.0"

DESCRIPTION = "Audio Files (WAV format) of the project <a href='https://doi.org/10.5281/zenodo.4309141'>Vanuatu Voices</a> "\
    + "which presents phonetically-transcribed primary recordings, from numerous villages "\
    + "throughout different islands, to both document and exhibit the extensive variation "\
    + "and unparalleled diversity of the Vanuatu languages."\
    + "<br /><br />Available online at: <a href='{2}'>{2}</a>"\
    + "<br />GitHub repository: <a href='{0}{1}'>{0}{1}/tree/v{3}</a>"

COMMUNITIES = sorted(set(['lexibank']))


def register(parser):
    parser.add_argument(
        '--mimetype',
        choices=['wav', 'ogg', 'mp3'],
        default=None,
    )
    parser.add_argument(
        '-l', '--list',
        help="List available mimetypes and file number and size",
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--out',
        help="Directory to which to download the audio files.",
        type=PathType(type='dir'),
        default=pathlib.Path('.')
    )
    parser.add_argument(
        '--create-release',
        help="Switch to create {id}_audio directory containing audio.zip, README.md and .zenodo.json for releasing on zenodo.",
        action='store_true',
        default=False,
    )
    parser.add_argument(
        '--update-zenodo',
        help="Deposit ID to update metadata by using {id}_audio/zendo.json.",
        required=False,
        default=None,
    )


def download(url, target):
    assert not target.exists()
    urlretrieve(url, str(target))


def create_download_thread(url, target):
    while threading.active_count() > 5:
        time.sleep(0.1)
    download_thread = threading.Thread(target=download, args=(url, target))
    download_thread.start()


def run(args):
    ds = Dataset().cldf_reader()

    release_dir = args.out / '{0}_audio'.format(Dataset().id)
    zenodo_file_name = 'zenodo.json'

    if args.list:
        size = collections.Counter()
        number = collections.Counter()
    else:
        f2c = {r['ID']: r['Parameter_ID'] for r in ds['FormTable']}
        audio = args.out / 'audio'
        audio.mkdir(exist_ok=True)

    if not args.update_zenodo:
        for row in tqdm.tqdm([r for r in ds['media.csv']]):
            if args.list:
                size[row['mimetype']] += int(row['size'])
                number.update([row['mimetype']])
            else:
                d = audio / f2c[row['Form_ID']]
                d.mkdir(exist_ok=True)
                url = ds.get_row_url('media.csv', row)
                target = d / '{}.{}'.format(row['ID'], url.split('.')[-1])
                if (not target.exists()) or md5(target) != row['ID']:
                    if (args.mimetype is None) or target.suffix.endswith(args.mimetype):
                        create_download_thread(url, target)

    if args.list:
        for k, v in size.most_common():
            print('\t'.join([k, str(number[k]), format_size(v)]))

    if args.create_release:
        assert audio.exists(), 'No folder "audio" found in {0}'.format(audio.resolve())

        release_dir.mkdir(exist_ok=True)

        args.log.info('creating audio ZIP archive per parameter folder ...')
        try:
            zipf = zipfile.ZipFile(str(release_dir / 'audio.zip'), 'w', zipfile.ZIP_DEFLATED)
            fp = args.out
            for root, dirs, files in tqdm.tqdm(os.walk(audio)):
                for f in files:
                    if not f.startswith('.') and not f.startswith('__')\
                            and ((args.mimetype is None) or f.endswith(args.mimetype)):
                        zipf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), fp))
            zipf.close()
        except Exception as e:
            args.log.error(e)
            raise

        def contrib(d):
            return {k: v for k, v in d.items() if k in {'name', 'affiliation', 'orcid', 'type'}}

        with jsonlib.update(release_dir / zenodo_file_name, indent=4, default=collections.OrderedDict()) as md:
            contribs = Dataset().dir / 'CONTRIBUTORS.md'
            creators, contributors = get_creators_and_contributors(
                contribs.read_text(encoding='utf8') if contribs.exists() else '', strict=False)
            if creators:
                md['creators'] = [contrib(p) for p in creators]
            if contributors:
                md['contributors'] = [contrib(p) for p in contributors]
            if COMMUNITIES:
                md['communities'] = [
                    {'id': community_id} for community_id in COMMUNITIES]
            md.update(
                {
                    'title': '{0} Audio Files'.format(Dataset().metadata.title),
                    'access_right': 'open',
                    'keywords': sorted(set(md.get('keywords', []) + ['linguistics'])),
                    'upload_type': 'video',
                    'version': VERSION,
                    'related_identifiers': [
                        {
                            'scheme': 'doi',
                            'identifier': '10.5281/zenodo.4309141',
                            'relation': 'isPartOf'
                        },
                        {
                            'scheme': 'url',
                            'identifier': '{0}{1}/tree/v{2}'.format(GITHUB_PREFIX, Dataset().id, VERSION),
                            'relation': 'isSupplementTo'
                        },
                    ],
                }
            )
            if Dataset().metadata.url:
                md['related_identifiers'].append({
                    'scheme': 'url', 'identifier': Dataset().metadata.url, 'relation': 'isAlternateIdentifier'})
            md['description'] = html.escape(DESCRIPTION.format(
                GITHUB_PREFIX, Dataset().id, Dataset().metadata.url if Dataset().metadata.url else '', VERSION))

            license_md = ''
            if Dataset().metadata.zenodo_license:
                md['license'] = {'id': Dataset().metadata.zenodo_license}
                license_md = LISENCE.format(Dataset().metadata.zenodo_license)

            DataDir(release_dir).write('README.md', RELEASE_NOTE.format(
                md['title'], GITHUB_PREFIX, Dataset().id, Dataset().metadata.title, license_md))

    if args.update_zenodo:
        assert release_dir.exists()
        assert (release_dir / zenodo_file_name).exists()

        md = {}
        md.update(jsonlib.load(release_dir / zenodo_file_name))

        api_url = API_URL
        zenodo_url = api_url.replace('api/', '')

        args.log.info('Updating Deposit ID {0} on {1} with:'.format(args.update_zenodo, zenodo_url))
        api = Zenodo(api_url=api_url, access_token=ACCESS_TOKEN)
        rec = api.record_from_id('{0}record/{1}'.format(zenodo_url, args.update_zenodo))
        args.log.info('  DOI:   ' + rec.metadata.doi)
        args.log.info('  Title: ' + rec.metadata.title)
        args.log.info('  Date:  ' + rec.metadata.publication_date)
        args.log.info('  Files: ' + ', '.join([f.key for f in rec.files]))
        p = input("Proceed? [y/N]: ")
        if p.lower() == 'y':
            dep = api.update_deposit(args.update_zenodo, **md)
            if dep.state != zenodoclient.models.PUBLISHED:
                api.publish_deposit(dep)
            args.log.info('Updated successfully')
