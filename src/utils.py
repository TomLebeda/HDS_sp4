import pandas as pd
from enum import Enum
from typing import Optional, Tuple

PATH_RYCHTARKA_ACTUAL = "./rychtarka-actual.csv"
PATH_NOVE_DIVADLO_ACTUAL = "./novedivadlo-actual.csv"
PATH_RYCHTARKA_FULL = "./rychtarka-full.csv"
PATH_NOVE_DIVADLO_FULL = "./novedivadlo-full.csv"
weekday_cz = ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobotu", "neděli"]

class SpotState(Enum):
    AVAILABLE = "volných"
    NOT_AVAILABLE = "obsazených"

class ParkHouse(Enum):
    RYCHTARKA = "Rychtářka"
    NOVE_DIVADLO = "Nové Divadlo"

class State(Enum):
    INIT = 0 # initial state
    IDLE = 1 # waiting for user to speak
    COMMAND = 2 # processing command
    QUESTION = 3 # processing question
    PENDING = 4 # waiting for user to fill missing information

class Command(Enum):
    HELP = "help" # say help
    QUIT = "quit" # end the dialog

class Question(Enum):
    CAPACITY = "QUESTION_capacity" # what is the capacity of [parkhouse] -> int
    HOW_MANY = "QUESTION_how_many" # how many [spot_state] are at [time] in [parkhouse] -> int
    ARE_FREE = "QUIESTION_exist" # are there any free spots at [time] in [parkhouse] -> bool
    ARE_AT_LEAST = "QUESTION_at_least" # are there at least [int] [spot_state] spots at [time] in [parkhouse] -> bool
    WHERE_IS_MORE = "QUESTION_where" # where is more [spot_state] spots at [time] -> parkhouse

class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6

def get_spot_count(park_house: ParkHouse, at_time: Optional[pd.Timestamp], at_day_of_week: Optional[DayOfWeek], at_date: Optional[pd.Timestamp], spot_state: Optional[SpotState]) -> Tuple[int, str]:
    cap, _ = get_capacity(park_house)
    if spot_state is None:
        spot_state = SpotState.AVAILABLE
    if at_time is None and at_day_of_week is None and at_date is None:
        # given nothing -> current
        data = load_csv(PATH_RYCHTARKA_ACTUAL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
        available = int(data.loc[0, "volno"])
        num = available if spot_state is SpotState.AVAILABLE else cap - available
        resp = f"V parkovacím domě {park_house.value} je právě {num} {spot_state.value} míst."
        return num, resp
    elif at_time is None and at_day_of_week is None and at_date is not None:
        # given date -> average at given date
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.date == at_date.date())]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bylo {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} míst."
        return num, resp
    elif at_time is None and at_day_of_week is not None and at_date is None:
        # given day_of_week -> average at given day of week
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.dayofweek == at_day_of_week)]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bývá v {weekday_cz[at_day_of_week.value]} průměrně {num} {spot_state} míst."
        return num, resp
    elif at_time is None and at_day_of_week is not None and at_date is not None:
        # given day_of_week and date -> average at given date
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.date == at_date.date())]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bylo {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} míst."
        return num, resp
    elif at_time is not None and at_day_of_week is None and at_date is None:
        # given time -> average at given time
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.hour == at_time.hour)]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bývá kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} míst."
        return num, resp
    elif at_time is not None and at_day_of_week is None and at_date is not None:
        # given time and date -> average at given time on given date
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.hour == at_time.hour) & (data["datum_aktualizace"].dt.date == at_date.date())]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bylo {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} míst."
        return num, resp
    elif at_time is not None and at_day_of_week is not None and at_date is None:
        # given time and day_of_week -> average at given time of given day of week
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.hour == at_time.hour) & (data["datum_aktualizace"].dt.dayofweek == at_day_of_week)]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bývá v {weekday_cz[at_day_of_week.value]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} míst."
        return num, resp
    elif at_time is not None and at_day_of_week is not None and at_date is not None:
        # given time and day_of_week and date -> average at given time on given date
        data = load_csv(PATH_RYCHTARKA_FULL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_FULL)
        filtered = data[(data["datum_aktualizace"].dt.hour == at_time.hour) & (data["datum_aktualizace"].dt.date == at_date.date())]
        avg_available = int(filtered.mean()["volno"])
        num = avg_available if spot_state is SpotState.AVAILABLE else cap - avg_available
        resp = f"V parkovacím domě {park_house.value} bylo {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} míst."
        return num, resp

    # this shouldn't happen, but Python LSP is paranoid
    return -1, "Pro vaši otázku bohužel nejsou dostupná vhodná data."

def load_csv(path: str) -> pd.DataFrame:
    data = pd.read_csv(path)
    data["datum_aktualizace"] = pd.to_datetime(data["datum_aktualizace"], format="%Y-%m-%d %H:%M:%S")
    return data

def get_capacity(park_house: ParkHouse) -> Tuple[int, str]:
    data = load_csv(PATH_RYCHTARKA_ACTUAL) if park_house is ParkHouse.RYCHTARKA else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    capacity = data.loc[0, "Kapacita"]
    resp = f"Kapacita parkovacího domu {park_house.value} je {capacity} míst."
    return capacity, resp

