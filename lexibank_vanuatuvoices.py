import re
import sys
import pathlib
import itertools
import collections
import dataclasses
from typing import Optional

from pylexibank import Dataset as BaseDataset
from pylexibank import Language, Concept, Lexeme
from pylexibank import FormSpec
from pylexibank import progressbar
from csvw.dsv import reader

MEDIA_DEPOSIT_ID = "23015980"
media_doi = f"10.5281/zenodo.{MEDIA_DEPOSIT_ID}"
ROLE_MAP = {
    'ContributorPhoneticTranscriptionBy': 'phonetic_transcriptions',
    'ContrbutorPhoneticTranscriptionBy': 'phonetic_transcriptions',
    'ContrbutorRecordedBy': 'recording',
    'ContributorRecordedBy1': 'recording',
    'ContributorSoundEditingBy': 'sound_editing',
    'ContrbutorSoundEditingBy': 'sound_editing',
    'ContributorRecordedBy2': 'recording',
}

def media_file(bs, fid):
    digit = bs["objid"][6]
    return {
        'ID': bs['ID'],
        'Name': bs['Name'],
        'Download_URL': f'https://zenodo.org/records/{MEDIA_DEPOSIT_ID}/files/vv_media_{digit}.zip',
        'Path_In_Zip': f'{digit}/{bs["objid"]}/{bs["Name"]}',
        'Media_Type': 'audio/x-wav' if bs['mimetype'] == 'audio/wav' else bs['mimetype'],
        'size': bs['size'],
        'Form_ID': fid,
    }

Rule = collections.namedtuple('Rule', 'lhs rhs')

GRAPHEME_RULES = [
    Rule(['n-n'], ['n', '-', 'n']),
    Rule(['naᵐ', '_', 'batina'], ['n', 'a', '_', 'ᵐb', 'a', 't', 'i', 'n', 'a']),
    Rule(['ʃ', '_', 'ʰovi'], ['ʃ', 'o', 'v', 'i']),
    Rule(['ne-βulʉ-'], ['n', 'e', '-', 'β', 'u', 'l', 'ʉ', '-']),
    Rule(['t', '-͡s', 'ɪ'], ['t', '-', 's', 'ɪ']),
    Rule(['-mᵐẽ'], ['-', 'ᵐm', 'ẽ']),
    Rule([chr(794)], []),  # ◌̚
]

GRAPHEME_REPLACEMENTS = {
    'ⁿᵈr': 'ⁿdʳ',
    'ⁿᵈɾ': 'ⁿdʳ',
    'ⁿᵈɹ': 'ⁿdʳ',
    'ᵈr': 'r',
}


class MalformedRule(Exception):
    """Error for when a user passes in an invalid rule object."""


def _apply_rule_iter(rule, items):
    index = 0
    while index < len(items):
        rule_index = 0
        while (
            rule_index < len(rule.lhs)
            and index + rule_index < len(items)
            and items[index+rule_index] == rule.lhs[rule_index]
        ):
            rule_index += 1
        if rule_index == len(rule.lhs):
            yield from rule.rhs
            index += rule_index
        else:
            yield items[index]
            index += 1


def apply_rule(rule, items):
    if not rule.lhs:
        raise MalformedRule('Left-hand-side of a transformation rule must not be empty')
    return list(_apply_rule_iter(rule, items))


def graphemes_to_orthography(grapheme_correspondance, lexeme):
    segments = re.sub('_+', ' _ ', lexeme['Graphemes'].lstrip('^').rstrip('$')).split()

    for rule in GRAPHEME_RULES:
        segments = apply_rule(rule, segments)

    unknown_segments = set()
    graphemes = []
    for segment in segments:
        if segment == '-':
            grapheme = segment
        elif segment == '_':
            grapheme = ' '
        elif (replacement := GRAPHEME_REPLACEMENTS.get(segment)):
            grapheme = grapheme_correspondance[replacement]
        elif segment in grapheme_correspondance:
            grapheme = grapheme_correspondance[segment]
        else:
            unknown_segments.add(segment)
            grapheme = segment
        graphemes.append(grapheme)
    if unknown_segments:
        print(
            'unknown segments:',
            '; '.join(sorted(unknown_segments)),
            file=sys.stderr)

    return ''.join(graphemes)


@dataclasses.dataclass
class CustomLanguage(Language):
    LongName: Optional[str] = None
    IsProto: Optional[str] = None
    Island: Optional[str] = None


@dataclasses.dataclass
class CustomConcept(Concept):
    Bislama_Gloss: Optional[str] = None
    Concepticon_SemanticField: Optional[str] = None


@dataclasses.dataclass
class CustomLexeme(Lexeme):
    Orthography: Optional[str] = None
    Bislama_Gloss: Optional[str] = None
    Concepticon_SemanticField: Optional[str] = None


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "vanuatuvoices"
    form_spec = FormSpec(
            replacements=[
                (" -", "-"),  # space and dash
                ("- ", "-"),
                ("\u031at", "t\u031a"),   # inverted diacritic
                ("--", "-"),  # double dash
                ("\u0306", ""),  # cannot be captured in orthoprofile
                ("\u033c", ""),
                ("ɸ̆", "ɸ"),
                (" ", "_"),
                ],
            missing_data=['..', '►']
            )

    concept_class = CustomConcept
    language_class = CustomLanguage
    lexeme_class = CustomLexeme

    def cmd_makecldf(self, args):
        self.dir.joinpath('NOTES.md').write_text('\n'.join([
            "Associated sound files are available in a separate dataset at",
            f"DOI: [{media_doi}](https://doi.org/{media_doi})"
        ]), encoding='utf8')
        grapheme_correspondance = {
            r['VV_grapheme']: r['orthography'] for r in
            self.etc_dir.read_csv('graphemes-unique-correspondances.csv', dicts=True)}

        sound_per_word = collections.defaultdict(
            lambda: collections.defaultdict(list))
        for row in reader(self.raw_dir / 'media.csv', dicts=True):
            lid, pid, n = row['Form_ID'].split('-')
            sound_per_word[lid, pid][int(n)].append(row)

        with args.writer as ds:
            self.schema(ds.cldf)
            ds.add_sources()

            for concept in self.concepts:
                del concept['IndexInSource']
                ds.add_concept(**concept)

            known_param_ids = set([d['ID'] for d in ds.objects['ParameterTable']])


            for lang_dir in progressbar(
                    sorted((self.raw_dir / 'data').iterdir(), key=lambda f: f.name),
                    desc="adding new data"):

                if lang_dir.name.startswith('.') or not (lang_dir / 'languages.csv').exists():
                    continue

                lang_id = lang_dir.name
                language = next(reader(lang_dir / 'languages.csv', dicts=True))
                source = language['Source']
                del language['Source']
                del language['ORG_LG_NAME']
                if 'IndexInSource' in language:
                    del language['IndexInSource']
                ds.add_language(**language)

                # Do not sort data.csv files - form id index refers to import
                for i, row in enumerate(lang_dir.read_csv('data.csv')):
                    value = row[0].strip()
                    if i == 0 or value == "►":
                        continue
                    param_id = row[1].strip()
                    if param_id not in known_param_ids:
                        continue
                    new = ds.add_form(
                        Language_ID=lang_id,
                        Local_ID='',
                        Parameter_ID=param_id,
                        Value=value,
                        Form=self.form_spec.clean(self.lexemes.get(value, value)),
                        Loan=False,
                        Source=source,
                    )
                    new['Orthography'] = graphemes_to_orthography(grapheme_correspondance, new)

                    if (lang_id, param_id) in sound_per_word:
                        key = list(sound_per_word[lang_id, param_id].keys())[0]
                        for bs in sorted(sound_per_word[lang_id, param_id][key], key=lambda i: i['mimetype']):
                            ds.objects['MediaTable'].append(media_file(bs, new['ID']))
                        del sound_per_word[lang_id, param_id][key]
                        if not sound_per_word[lang_id, param_id]:
                            del sound_per_word[lang_id, param_id]
            assert not sound_per_word

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

    def schema(self, cldf):
        t = cldf.add_component(
            'MediaTable',
            {'name': 'size', 'datatype': 'integer'},
            {
                'name': 'Form_ID',
                'required': True,
                'propertyUrl': 'http://cldf.clld.org/v1.0/terms.rdf#formReference',
                'datatype': 'string'
            },
        )
        t.common_props['dc:identifier'] = f"https://doi.org/{media_doi}"
        cldf.remove_columns('MediaTable', 'Description')
        cldf.add_component(
            'ContributionTable',
            'phonetic_transcriptions',
            'recording',
            'sound_editing',
            {
                "name": "Language_ID",
                "required": True,
                "propertyUrl": "http://cldf.clld.org/v1.0/terms.rdf#languageReference",
                "datatype": "string"
            },
        )
        cldf.remove_columns('ContributionTable', 'Name')
        cldf.remove_columns('ContributionTable', 'Description')
        cldf.remove_columns('ContributionTable', 'Contributor')
        cldf.remove_columns('ContributionTable', 'Citation')
