import pathlib
import attr
import itertools
import csv

from pylexibank.providers.sndcmp import SNDCMP as BaseDataset
from pylexibank.providers.sndcmp import SNDCMPConcept, SNDCMPLanguage
from pylexibank import FormSpec
from pylexibank import progressbar

ROLE_MAP = {
    'ContributorPhoneticTranscriptionBy': 'phonetic_transcriptions',
    'ContrbutorPhoneticTranscriptionBy': 'phonetic_transcriptions',
    'ContrbutorRecordedBy': 'recording',
    'ContributorRecordedBy1': 'recording',
    'ContributorSoundEditingBy': 'sound_editing',
    'ContrbutorSoundEditingBy': 'sound_editing',
    'ContributorRecordedBy2': 'recording',
}


@attr.s
class CustomLanguage(SNDCMPLanguage):
    Island = attr.ib(default=None)


@attr.s
class CustomConcept(SNDCMPConcept):
    Bislama_Gloss = attr.ib(default=None)
    Concepticon_SemanticField = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "vanuatuvoices"
    form_spec = FormSpec(
            replacements=[
                (" -", "-"), # space and dash
                ("- ", "-"),
                ("\u031at", "t\u031a"), # inverted diacritic
                ("--", "-"), # double dash
                ("\u0306", ""), # cannot be captured in orthoprofile
                ("\u033c", ""),
                ("ɸ̆", "ɸ"),
                (" ", "_"),
                ],
            missing_data=['..', '►']
            )

    study_name = "Vanuatu"
    second_gloss_lang = "Bislama"
    source_id_array = ["Shimelman2019"]
    create_cognates = False

    form_placeholder = '►'

    concept_class = CustomConcept
    language_class = CustomLanguage

    def cmd_makecldf(self, args):
        BaseDataset.form_spec = self.form_spec
        BaseDataset.cmd_makecldf(self, args)
        # TODO: discuss if this modification should not better be made at the
        # level of the provider script in lexibank!
        for row in progressbar(args.writer.objects["FormTable"], desc="refine"):
            row["Form"] = self.form_spec.clean(row["Form"])
            row["Segments"] = self.tokenizer(row, row["Form"])

        data_path = self.raw_dir / 'data'
        known_lang_ids = set([d['ID'] for d in args.writer.objects['LanguageTable']])
        known_param_ids = set([d['ID'] for d in args.writer.objects['ParameterTable']])

        media = []
        for m in args.writer['media.csv']:
            media.append(dict(m))

        sound_cat = self.raw_dir.read_json('catalog_vv.json')
        sound_map = dict()
        for k, v in sound_cat.items():
            sound_map[v['metadata']['name']] = k

        for lang_dir in progressbar(
                sorted(data_path.iterdir(), key=lambda f: f.name),
                desc="adding new data"):

            if lang_dir.name.startswith('.') or not (lang_dir / 'languages.csv').exists():
                continue

            lang_id = lang_dir.name
            with open(lang_dir / 'languages.csv') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    language = row
                    break
            source = language['Source']
            del language['Source']
            del language['ORG_LG_NAME']
            if lang_id not in known_lang_ids:
                args.writer.add_language(**language)

            seen_values = {}
            with open(lang_dir / 'data.csv') as f:
                reader = csv.reader(f)
                for i, row in enumerate(reader):
                    if i > 0 and row[0].strip() != "►":
                        p = row[1].strip()
                        if p in seen_values:
                            seen_values[p] += 1
                            idx = '__{}'.format(seen_values[p])
                        else:
                            seen_values[p] = 1
                            idx = ''
                        if p in known_param_ids and row[0].strip() != "►":
                            frm = self.form_spec.clean(self.lexemes.get(row[0].strip(),
                                row[0].strip()))
                            new = args.writer.add_form(
                                Language_ID=lang_id,
                                Local_ID='',
                                Parameter_ID=p,
                                Value=row[0].strip(),
                                Form=frm,
                                Loan=False,
                                Source=source,
                                Variant_Of=None,
                            )
                            media_id = '{}_{}{}'.format(lang_id, p, idx)
                            if media_id in sound_map:
                                for bs in sorted(sound_cat[sound_map[media_id]]['bitstreams'],
                                                 key=lambda x: x['content-type']):
                                    media.append({
                                        'ID': bs['checksum'],
                                        'fname': bs['bitstreamid'],
                                        'objid': sound_map[media_id],
                                        'mimetype': bs['content-type'],
                                        'size': bs['filesize'],
                                        'Form_ID': new['ID']
                                    })

        args.writer.write(
            **{'media.csv': media}
        )

        args.writer.cldf.add_table(
            'contributions.csv',
            {
                'name': 'ID',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
                'valueUrl': 'https://cdstar.eva.mpg.de/bitstreams/{objid}/{fname}',
            },
            'phonetic_transcriptions',
            'recording',
            'sound_editing',
            {
                "name": "Language_ID",
                "required": True,
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#languageReference",
                "datatype": "string"
            },
            primaryKey=['ID']
        )

        args.writer.cldf.add_foreign_key(
            'contributions.csv', 'Language_ID', 'LanguageTable', 'ID', )
        for lid, contribs in itertools.groupby(
            sorted(
                self.raw_dir.read_csv('contributions.csv', dicts=True),
                key=lambda r: (r['Language_ID'], r['Role'])),
            lambda r: r['Language_ID']
        ):
            res = dict(
                ID=lid,
                phonetic_transcriptions='',
                recording='',
                sound_editing='',
                Language_ID=lid,
            )
            for contrib in contribs:
                k = ROLE_MAP[contrib['Role']]
                if res[k]:
                    res[k] += ' and '
                res[k] += contrib['Contributor']
            args.writer.objects['contributions.csv'].append(res)
