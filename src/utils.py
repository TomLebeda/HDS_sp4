import pandas as pd
from enum import Enum
from typing import Optional, Tuple

PATH_RYCHTARKA_ACTUAL = './rychtarka-actual.csv'
PATH_NOVE_DIVADLO_ACTUAL = './novedivadlo-actual.csv'
PATH_RYCHTARKA_FULL = './rychtarka-full.csv'
PATH_NOVE_DIVADLO_FULL = './novedivadlo-full.csv'
TIMEOUT_SECONDS = 5


class SpotState(Enum):
    AVAILABLE = 'volných'
    NOT_AVAILABLE = 'obsazených'


class ParkHouse(Enum):
    RYCHTARKA = 'Rychtářka'
    NOVE_DIVADLO = 'Nové Divadlo'


class State(Enum):
    INIT = 0   # initial state
    IDLE = 1   # waiting for user to speak
    COMMAND = 2   # processing command
    QUESTION = 3   # processing question
    PENDING = 4   # waiting for user to fill missing information


class Command(Enum):
    HELP = 'help'   # say help
    QUIT = 'quit'   # end the dialog


class Question(Enum):
    CAPACITY = (
        'QUESTION_capacity'  # what is the capacity of [parkhouse] -> int
    )
    HOW_MANY = 'QUESTION_how_many'   # how many [spot_state] are at [time] in [parkhouse] -> int
    ARE_FREE = 'QUESTION_exist'   # are there any free spots at [time] in [parkhouse] -> bool


class DayOfWeek(Enum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


weekday_cz = [
    'pondělí',
    'úterý',
    'středa',
    'čtvrtek',
    'pátek',
    'sobotu',
    'neděli',
]
timeout_helps = [
    [
        'Mluvíte s informačním systémem parkovacíh domů Rychtářka a Nové Divadlo',
        'Ptejte se prosím nebo požádejte o nápovědu.',
    ],
    [
        'Mluvíte s informačním systémem parkovacíh domů Rychtářka a Nové Divadlo',
        'Můžete se zeptat na kapacitu, počet obsazených a plných míst v různé dny a časy.',
    ],
    [
        'Mluvíte s informačním systémem parkovacíh domů Rychtářka a Nové Divadlo',
        'Můžete se zeptat na kapacitu, počet obsazených a plných míst v různé dny a časy',
        'Ptejte se prosím, jinak bude dialog ukončen.'
    ],
]

# keep all forms of length 3 for easier usage later
spot_states = dict()
spot_states[SpotState.AVAILABLE] = ['volné', 'volná', 'volných']
spot_states[SpotState.NOT_AVAILABLE] = ['obsazené', 'obsazená', 'obsazených']
word_is = ['je', 'jsou', 'je']
word_was = ['bylo', 'byla', 'bylo']
word_is_usually = ['bývá', 'bývají', 'bývá']
word_spot = ['místo', 'místa', 'míst']


def get_spot_count(
    park_house: ParkHouse,
    at_time: Optional[pd.Timestamp],
    at_day_of_week: Optional[DayOfWeek],
    at_date: Optional[pd.Timestamp],
    spot_state: Optional[SpotState],
) -> Tuple[int, str]:
    cap, _ = get_capacity(park_house)
    data_actual = (
        load_csv(PATH_RYCHTARKA_ACTUAL)
        if park_house is ParkHouse.RYCHTARKA
        else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    )
    data_full = (
        load_csv(PATH_RYCHTARKA_FULL)
        if park_house is ParkHouse.RYCHTARKA
        else load_csv(PATH_NOVE_DIVADLO_FULL)
    )
    # OpenData killed the URL where actual fresh data was fetched from right before I had this finished.
    # But it wouldn't be fun if everything went as planned, right?
    # So this work-around fakes fresh data by shift time-stamp of all rows so that the newest date is matching today's date.
    time_shift = (
        pd.Timestamp.now().date()
        - data_actual.loc[0, 'datum_aktualizace'].date()
    )
    data_actual['datum_aktualizace'] = (
        data_actual['datum_aktualizace'] + time_shift
    )
    data_full['datum_aktualizace'] = (
        data_full['datum_aktualizace'] + time_shift
    )
    data_merged = data_actual.merge(data_full, how='outer')
    try:
        if spot_state is None:
            spot_state = SpotState.AVAILABLE
        if at_time is None and at_day_of_week is None and at_date is None:
            # given nothing -> current state
            available = int(data_actual.loc[0, 'volno'])
            num = (
                available
                if spot_state is SpotState.AVAILABLE
                else cap - available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_is[0]} právě {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_is[1]} právě {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_is[2]} právě {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is None and at_day_of_week is None and at_date is not None
        ):
            # given date -> average at given date
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.date == at_date.date())
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_was[0]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_was[1]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_was[2]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is None and at_day_of_week is not None and at_date is None
        ):
            # given day_of_week -> average at given day of week
            filtered = data_merged[
                (
                    data_merged['datum_aktualizace'].dt.dayofweek
                    == at_day_of_week.value
                )
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[0]} v {weekday_cz[at_day_of_week.value]} průměrně {num} {spot_state} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[1]} v {weekday_cz[at_day_of_week.value]} průměrně {num} {spot_state} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[2]} v {weekday_cz[at_day_of_week.value]} průměrně {num} {spot_state} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is None
            and at_day_of_week is not None
            and at_date is not None
        ):
            # given day_of_week and date -> average at given date
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.date == at_date.date())
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_was[0]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_was[1]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_was[2]} {at_date.day}.{at_date.month}. průměrně {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is not None and at_day_of_week is None and at_date is None
        ):
            # given time -> average at given time
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.hour == at_time.hour)
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[0]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[1]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[2]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is not None
            and at_day_of_week is None
            and at_date is not None
        ):
            # given time and date -> average at given time on given date
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.hour == at_time.hour)
                & (data_merged['datum_aktualizace'].dt.date == at_date.date())
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_was[0]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_was[1]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_was[2]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is not None
            and at_day_of_week is not None
            and at_date is None
        ):
            # given time and day_of_week -> average at given time of given day of week
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.hour == at_time.hour)
                & (
                    data_merged['datum_aktualizace'].dt.dayofweek
                    == at_day_of_week.value
                )
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[0]} v {weekday_cz[at_day_of_week.value]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[1]} v {weekday_cz[at_day_of_week.value]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_is_usually[2]} v {weekday_cz[at_day_of_week.value]} kolem {at_time.hour}. hodiny průměrně {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        elif (
            at_time is not None
            and at_day_of_week is not None
            and at_date is not None
        ):
            # given time and day_of_week and date -> average at given time on given date
            filtered = data_merged[
                (data_merged['datum_aktualizace'].dt.hour == at_time.hour)
                & (data_merged['datum_aktualizace'].dt.date == at_date.date())
            ]
            avg_available = int(filtered.mean()['volno'])
            num = (
                avg_available
                if spot_state is SpotState.AVAILABLE
                else cap - avg_available
            )
            # the data are shitty, this is to prevent negative values
            num = max(0, num)
            if num == 1:
                resp = f'V parkovacím domě {park_house.value} {word_was[0]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[0]}.'
            elif num in [2, 3, 4]:
                resp = f'V parkovacím domě {park_house.value} {word_was[1]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[1]}.'
            else:
                resp = f'V parkovacím domě {park_house.value} {word_was[2]} {at_date.day}.{at_date.month}. kolem {at_time.hour}. hodiny {num} {spot_state.value} {word_spot[2]}.'
            return num, resp
        # this shouldn't happen, but Python LSP is paranoid
        return -1, 'Pro vaši otázku bohužel nejsou dostupná data.'
    except:
        # this will happen when no data remain after filtration
        return -1, 'Pro vaši otázku bohužel nejsou dostupná data.'


def load_csv(path: str) -> pd.DataFrame:
    data = pd.read_csv(path)
    data['datum_aktualizace'] = pd.to_datetime(
        data['datum_aktualizace'], format='%Y-%m-%d %H:%M:%S'
    )
    return data


def get_capacity(park_house: ParkHouse) -> Tuple[int, str]:
    data = (
        load_csv(PATH_RYCHTARKA_ACTUAL)
        if park_house is ParkHouse.RYCHTARKA
        else load_csv(PATH_NOVE_DIVADLO_ACTUAL)
    )
    capacity = data.loc[0, 'Kapacita']
    resp = f'Kapacita parkovacího domu {park_house.value} je {capacity} míst.'
    return capacity, resp
