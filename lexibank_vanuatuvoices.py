import pathlib
import attr
import itertools

from pylexibank.providers.sndcmp import SNDCMP as BaseDataset
from pylexibank.providers.sndcmp import SNDCMPConcept, SNDCMPLanguage
from pylexibank import FormSpec

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


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "vanuatuvoices"
    form_spec = FormSpec(
            replacements=[
                ("\u0306", ""), # cannot be captured in orthoprofile 
                ("\u033c", ""),
                ("ɸ̆", "ɸ"),
                ],
            missing_data=["►", '..']
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
        args.writer.cldf.add_table(
            'contributions.csv',
            {
                'name': 'ID',
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#id',
                'valueUrl': 'https://cdstar.shh.mpg.de/bitstreams/{objid}/{fname}',
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
