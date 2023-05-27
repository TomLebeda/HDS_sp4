import pandas as pd
from enum import Enum

PATH_RYCHTARKA_ACTUAL = "../rychtarka-actual.csv"
PATH_NOVE_DIVADLO_ACTUAL = "../novedivadlo-actual.csv"
PATH_RYCHTARKA_FULL = "../rychtarka-full.csv"
PATH_NOVE_DIVADLO_FULL = "../novedivadlo-full.csv"

class SpotState(Enum):
    AVAILABLE = 0
    NOT_AVAILABLE = 1

class ParkHouse(Enum):
    RYCHTARKA = "Rychtářka"
    NOVE_DIVADLO = "Nové Divadlo"

class State(Enum):
    INIT = 0 # initial state
    IDLE = 1 # waiting for user to speak
    HELP = 2 # say help
    QUIT = 3 # end the dialog
    QUESTION = 3 # processing question

class Question(Enum):
    CAPACITY = 1 # what is the capacity of [parkhouse] -> int
    HOW_MANY = 2 # how many [spot_state] are at [time] in [parkhouse] -> int
    ARE_FREE = 3 # are there any free spots at [time] in [parkhouse] -> bool
    ARE_AT_LEAST = 4 # are there at least [int] [spot_state] spots at [time] in [parkhouse] -> bool
    WHERE_IS_MORE = 5 # where is more [spot_state] spots at [time] -> parkhouse

class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

def get_available_at_time(park_house: ParkHouse, at_time: pd.Timestamp, at_day: DayOfWeek) -> int:
    data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
    target_hour = at_time.hour
    filtered = data[(data['datum_aktualizace'].dt.hour == target_hour) & (data['datum_aktualizace'].dt.dayofweek == at_day)]
    mean = filtered.mean()['volno']
    return int(mean)

def get_unavailable_at_time(park_house: ParkHouse, at_time: pd.Timestamp, at_day: DayOfWeek) -> int:
    available = get_available_at_time(park_house, at_time, at_day)
    cap = get_capacity(park_house)
    return cap - available

def where_is_more_available_currently() -> ParkHouse:
    return ParkHouse.RYCHTARKA if get_available_currently(ParkHouse.RYCHTARKA) >= get_available_currently(ParkHouse.NOVE_DIVADLO) else ParkHouse.NOVE_DIVADLO

def where_is_more_available_at_time(at_time: pd.Timestamp, at_day: DayOfWeek) -> ParkHouse:
    r = get_available_at_time(ParkHouse.RYCHTARKA, at_time, at_day)
    nd = get_available_at_time(ParkHouse.NOVE_DIVADLO, at_time, at_day)
    return ParkHouse.RYCHTARKA if r >= nd else ParkHouse.NOVE_DIVADLO

def load_csv(path: str) -> pd.DataFrame:
    data = pd.read_csv(path)
    data['datum_aktualizace'] = pd.to_datetime(data['datum_aktualizace'], format='%Y-%m-%d %H:%M:%S')
    return data

def get_available_currently(park_house: ParkHouse) -> int:
    data = load_csv(PATH_RYCHTARKA_ACTUAL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    available = data.loc[0, "volno"]
    return available
    
def get_unavailable_currently(park_house: ParkHouse) -> int:
    data = load_csv(PATH_RYCHTARKA_ACTUAL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    available = data.loc[0, "volno"]
    capacity = data.loc[0, "Kapacita"]
    return capacity - available

def get_capacity(park_house: ParkHouse) -> int:
    data = load_csv(PATH_RYCHTARKA_ACTUAL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    capacity = data.loc[0, "Kapacita"]
    return capacity

