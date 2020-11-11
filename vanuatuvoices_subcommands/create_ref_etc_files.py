"""
Generates reference files raw/concepts.csv and raw/languages.csv
"""
from cldfbench.cli_util import with_dataset, add_dataset_spec, add_catalog_spec


def register(parser):
    add_dataset_spec(parser)
    add_catalog_spec(parser, 'glottolog')
    add_catalog_spec(parser, 'concepticon')


def run(args):
    with_dataset(args, 'create_ref_etc_files')
