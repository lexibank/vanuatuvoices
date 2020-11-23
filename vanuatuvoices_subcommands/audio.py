"""
Download audio files.

Will create/use a directory structure
- audio
  |- <concept-ID>
     |- <media-IA>.<suffix>
"""
import time
import pathlib
import threading
import collections
from urllib.request import urlretrieve

from clldutils.path import md5
from clldutils.misc import format_size
from clldutils.clilib import PathType
import tqdm
from pycldf import Dataset

from lexibank_vanuatuvoices import Dataset


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

    if args.list:
        size = collections.Counter()
        number = collections.Counter()
    else:
        f2c = {r['ID']: r['Parameter_ID'] for r in ds['FormTable']}
        audio = args.out / 'audio'
        audio.mkdir(exist_ok=True)

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
