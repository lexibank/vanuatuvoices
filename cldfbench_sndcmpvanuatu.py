import pathlib
import attr

from pylexibank.providers.sndcmp import SNDCMP as BaseDataset
from pylexibank.providers.sndcmp import SNDCMPConcept

@attr.s
class CustomConcept(SNDCMPConcept):
    Bislama_Gloss = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "sndcmpvanuatu"

    study_name = "Vanuatu"
    second_gloss_lang = "Bislama"
    source_id_array = ["Shimelman2019"]
    create_cognates = False

    concept_class = CustomConcept

