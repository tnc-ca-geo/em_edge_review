import pytz

from logger import get_logger
from onboard_system.automated_reporting import settings
from onboard_system.species_registry import ILLEGAL_SPECIES

LOCAL_TZ = pytz.timezone(settings.LOCAL_TZ_NAME)

logger = get_logger(__name__)


def get_illegal_species_risk_features(counts_by_species: list) -> list:
    """Add risk features to each species in the dictionary.

    Args:
        counts_by_species (list): A list of dictionaries, each containing:
            - "fao_code": The FAO code of the species.
            - "RETAINED": Count of retained catches.
            - "VESSEL_DISCARD": Count of discarded catches.

    Returns:
        list: The input list with added keys for each species dictionary:
            - "is_illegal": Boolean indicating if the species is in the illegal species list.

    """
    for species in counts_by_species:
        species_fao_code = species.get("fao_code")
        species["is_illegal"] = species_fao_code in ILLEGAL_SPECIES
    return counts_by_species
