from dialog import EntityMap, SLUResult, SpeechCloudWS, Dialog
import logging
from utils import *
import pandas as pd
from typing import Optional

fakes = [
    'jaká je kapacita rychtářky',
    'a co nového divadla',
    'kolik bylo obsazených míst předevčírem v novém divadle',
    'kolik je obsazených míst v úterý novém divadle',
    'kolik bylo před deseti hodinama volných míst v novém divadle',
    'jsou v rychtářce nějaká volná místa v deset',
    'můžu zaparkovat v novém divadle v půl dvanáctý',
    'jsou v novém divadle nějaká obsazená místa',
    'jsou v rychtářce nějaká obsazená místa v úterý ve dvě hodiny',
    'jsou v novém divadle nějaká obsazená místa ve čtvrtek v půl jedné',
    'jaká je kapacita',
    'nového divadla',
    'kolik je volných míst v rychtářce',
    'a co obsazených míst',
    'a jaká je kapacita ve středu',
    'v rychtářce',
    'konec',
]


class MyDialog(Dialog):
    # attempt to use Rust-like typing to keep my sanity
    state: State
    question: Optional[Question]
    last_question: Optional[Question]
    parkhouse: Optional[ParkHouse]
    time: Optional[pd.Timestamp]
    day_of_week: Optional[DayOfWeek]
    command: Optional[Command]
    date: Optional[pd.Timestamp]
    spot_state: SpotState
    fake_index: int = 0
    timeouts: int = 0

    def __str__(self):
        return f'State:\t{self.state}\nQuest:\t{self.question}\nLastQ:\t{self.last_question}\nParkH:\t{self.parkhouse}\nTime:\t{self.time}\nWeekD:\t{self.day_of_week}\nDate:\t{self.date}\nCmd:\t{self.command}\nSpotS:\t{self.spot_state}'

    async def fake_input(self, text: str):
        # it"s sad that this method needs to exist like this
        logging.debug(f"faking input: '{text}'")
        await self.sc.asr_process_text(text=text)
        res = await self.wait_for_slu_result()
        return res

    async def init(self):
        logging.info('Entered init()')
        # setup variables:
        self.state = State.INIT
        self.question = None
        self.parkhouse = None
        self.time = None
        self.day_of_week = None
        self.last_question = None
        self.command = None
        self.date = None
        # assume that user wants to know about available spots by default
        self.spot_state = SpotState.AVAILABLE
        # setup grammars:
        await self.define_slu_grammars(
            [
                {
                    'entity': 'times',
                    'data': open('./data/times.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'weekdays',
                    'data': open('./data/weekdays.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'fractions',
                    'data': open('./data/fractions.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'time_words',
                    'data': open('./data/time_words.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'commands',
                    'data': open('./data/commands.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'other',
                    'data': open('./data/other.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'questions',
                    'data': open('./data/questions.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
                {
                    'entity': 'numbers',
                    'data': open('./data/numbers.abnf', 'rt').read(),
                    'type': 'abnf-inline',
                },
            ]
        )
        logging.info('Finished init()')

    async def finish_question(self):
        self.state = State.IDLE
        self.last_question = self.question
        self.question = None
        await self.synthesize_and_wait("Ještě něco dalšího?")

    def extract_data(self, slu: SLUResult):
        changed = False
        changed |= self.extract_parkhouse(slu.entities['other'])
        changed |= self.extract_spot_state(slu.entities['other'])
        changed |= self.extract_time(slu.entities['times'])
        changed |= self.extract_day_of_week(slu)
        changed |= self.extract_date(slu.entities['times'])
        # if something changed, repeat last question with new data
        if changed:
            if self.question is None:
                self.question = self.last_question
            self.state = State.QUESTION

    async def loop(self):
        # oh how nice it would be to have Rust match...
        logging.info('Entered loop()')
        while True:
            if self.state is State.INIT:
                logging.debug('entered INIT branch')
                await self.synthesize_and_wait(
                    'Dobrý den, tady informační systém pro parkovací domy Nové Divadlo a Rychtářka, můžete se ptát.'
                )
                self.state = State.IDLE

            elif self.state is State.COMMAND:
                logging.info('entered COMMAND branch')
                if self.command is Command.QUIT:
                    logging.info('entered QUIT branch')
                    await self.synthesize_and_wait('Nashledanou.')
                    return
                elif self.command is Command.HELP:
                    logging.info('entered HELP branch')
                    await self.synthesize_and_wait(
                        [
                            'Mluvíte s informačním systémem pro parkovací domy v Plzni.',
                            'Můžete se ptát na kapacitu a počty volných míst v parkovacích domech Rychtářka nebo Nové Divadlo v různé dny a časy.',
                            'Například můžete položit otázku "Jaká je kapacita v Rychtářce?" nebo "Kolik je volných míst v Novém Divadle?".'
                            'Můžete se ptát.'
                        ]
                    )
                    self.state = State.IDLE

            elif self.state is State.IDLE:
                logging.debug('entered IDLE branch')

                # slu = await self.fake_input(fakes[self.temp])
                # self.temp += 1
                await self.display("Listening...")
                slu = await self.recognize_and_wait_for_slu_result(
                    timeout=TIMEOUT_SECONDS
                )
                # according to "documentation", timeout should produce None, but it doesn't
                # so I manually check if the result is empty and count that as a timeout
                # it's nice when documentation is dependable
                if len(slu.entity_types) == 0:
                    logging.info('SLU Timeout.')
                    if self.timeouts < len(timeout_helps):
                        await self.synthesize_and_wait(
                            timeout_helps[self.timeouts]
                        )
                    else:
                        # after exhausting all timeouts, exit the dialog
                        self.state = State.COMMAND
                        self.command = Command.QUIT
                        continue
                    self.timeouts += 1
                    self.state = State.IDLE

                # check for commands
                new_command = (
                    self.extract_commands(slu.entities['commands'])
                    if slu.entities['commands']
                    else None
                )
                if new_command is not None:
                    self.state = State.COMMAND
                    self.command = new_command
                    continue   # don't bother with the rest, commands have priority

                # check for questions
                new_question = (
                    self.extract_question(slu.entities['questions'])
                    if slu.entities['questions']
                    else None
                )
                if new_question is not None:
                    # new question will reset all time info
                    self.time = None
                    self.date = None
                    self.day_of_week = None
                    self.state = State.QUESTION
                    self.question = new_question

                # extract data for the question
                self.extract_data(slu)
                logging.debug(f'current state: \n{self}')

            elif self.state is State.PENDING:
                logging.debug('entered PENDING branch')

                # slu = await self.fake_input(fakes[self.temp])
                # self.temp += 1
                await self.display("Listening...")
                slu = await self.recognize_and_wait_for_slu_result(
                    timeout=TIMEOUT_SECONDS
                )

                # current question can be overridden by command
                new_command = (
                    self.extract_commands(slu.entities['commands'])
                    if slu.entities['commands']
                    else None
                )
                if new_command is not None:
                    self.state = State.COMMAND
                    self.command = new_command
                    continue   # don"t bother with the rest, commands have priority

                # current question can be overridden by new question
                new_question = (
                    self.extract_question(slu.entities['questions'])
                    if slu.entities['questions']
                    else None
                )
                if new_question is not None:
                    self.question = new_question

                # hopefully the missing data will be filled in
                self.extract_data(slu)

                # return back to processing the current question
                self.state = State.QUESTION

            elif self.state is State.QUESTION:
                logging.debug('entered QUESTION branch')

                if self.question is Question.CAPACITY:
                    logging.debug(f'processing question: CAPACITY')
                    if self.parkhouse is None:
                        logging.debug(f'requirement missing: parkhouse')
                        await self.synthesize_and_wait(
                            'Který parkovací dům myslíte? Nové Divadlo, nebo Rychtářka?'
                        )
                        self.state = State.PENDING
                    else:
                        cap, resp = get_capacity(self.parkhouse)
                        logging.debug(f'RESPONSE: {resp}')
                        await self.synthesize_and_wait(resp)
                        await self.finish_question()

                elif self.question is Question.HOW_MANY:
                    logging.debug(f'processing question: HOW_MANY')
                    if self.parkhouse is None:
                        logging.debug(f'requirement missing: parkhouse')
                        await self.synthesize_and_wait(
                            'Který parkovací dům myslíte? Nové Divadlo, nebo Rychtářka?'
                        )
                        self.state = State.PENDING
                    else:
                        count, resp = get_spot_count(
                            self.parkhouse,
                            self.time,
                            self.day_of_week,
                            self.date,
                            self.spot_state,
                        )
                        logging.debug(f'RESPONSE: {resp}')
                        await self.synthesize_and_wait(resp)
                        await self.finish_question()

                elif self.question is Question.ARE_FREE:
                    logging.debug(f'processing question: ARE_FREE')
                    if self.parkhouse is None:
                        logging.debug(f'requirement missing: parkhouse')
                        await self.synthesize_and_wait(
                            'Který parkovací dům myslíte? Nové Divadlo, nebo Rychtářka?'
                        )
                        self.state = State.PENDING
                    else:
                        count, resp = get_spot_count(
                            self.parkhouse,
                            self.time,
                            self.day_of_week,
                            self.date,
                            self.spot_state,
                        )
                        if count > 0:
                            logging.debug(f'RESPONSE: Ano. {resp}')
                            await self.synthesize_and_wait(['Ano.', resp])
                        else:
                            logging.debug(f'RESPONSE: Ne. {resp}')
                            await self.synthesize_and_wait(
                                ['Ne.', resp]
                            )
                        await self.finish_question()

                else:
                    logging.warning(f'no question matched')
                    await self.synthesize_and_wait(
                        [
                            'Omlouvám se, tomu nerozumím'
                            'Zkuste se zeptat jinak, nebo požádejte o nápovědu.'
                        ]
                    )
                    self.state = State.IDLE

    def extract_spot_state(self, slu: EntityMap) -> bool:
        logging.info(f'extracting spot state from: {slu}')
        for s in slu.all:
            for p in SpotState:
                if s == p.name:
                    logging.debug(f'first match: {p}')
                    self.spot_state = p
                    return True
        logging.debug('no matching spot state found')
        return False   # this is the default one

    def extract_parkhouse(self, slu: EntityMap) -> bool:
        logging.info(f'extracting parkhouse from: {slu}')
        for s in slu.all:
            for p in ParkHouse:
                if s == p.value:
                    logging.debug(f'first match: {p}')
                    self.parkhouse = p
                    return True
        logging.debug('no matching parkhouse found')
        return False

    def extract_commands(self, slu: EntityMap) -> Optional[Command]:
        logging.info(f'extracting commands from: {slu}')
        for s in slu.all:
            for c in Command:
                if s == c.value:
                    logging.debug(f'first match: {c}')
                    return c
        logging.debug('no matching command found')
        return None

    def extract_question(self, slu: EntityMap) -> Optional[Question]:
        logging.debug(f'extracting questions from: {slu}')
        for s in slu.all:
            for q in Question:
                if s == q.value:
                    logging.debug(f'first match: {q}')
                    return q
        logging.debug('no matching question found')
        return None

    def extract_time(self, slu: EntityMap) -> bool:
        logging.debug(f'extracting time from: {slu}')
        # this is painful without static typing
        try:
            # this could be shortened with regex, but I would like to keep my sanity
            chunks = str(slu.first).split(':')
            if chunks[0] == 'add' and 'hod' in chunks and 'min' in chunks:
                self.time = pd.Timestamp.now() + pd.Timedelta(
                    year=0, hours=int(chunks[1]), minutes=int(chunks[3])
                )
                # relative time nullifies day of week and date
                self.day_of_week = None
                self.date = pd.Timestamp.today()
            elif (
                chunks[0] == 'subtract' and 'hod' in chunks and 'min' in chunks
            ):
                self.time = pd.Timestamp.now() - pd.Timedelta(
                    hours=int(chunks[1]), minutes=int(chunks[3])
                )
                self.day_of_week = (
                    None  # relative time nullifies day of week and date
                )
                self.date = pd.Timestamp.today()
            else:
                if self.time is None:
                    self.time = pd.Timestamp.now()
                self.time = self.time.replace(
                    hour=int(chunks[0]), minute=int(chunks[2])
                )
            return True
        except:
            return False

    def extract_date(self, slu: EntityMap) -> bool:
        logging.debug(f'extracting date from: {slu}')
        try:
            chunks = str(slu.first).split(':')
            if chunks[0] == 'add' and 'day' in chunks:
                self.date = pd.Timestamp.today() + pd.Timedelta(
                    days=int(chunks[1])
                )
                return True
            elif chunks[0] == 'subtract' and 'day' in chunks:
                self.date = pd.Timestamp.today() - pd.Timedelta(
                    days=int(chunks[1])
                )
                return True
            else:
                return False
        except:
            return False

    def extract_day_of_week(self, slu: SLUResult) -> bool:
        logging.debug(f'extracting day of week from: {slu.entities}')
        try:
            for s in slu.entities['weekdays'].all:
                for w in DayOfWeek:
                    if s == w.name:
                        logging.debug(f'first match: {w}')
                        self.day_of_week = w
                        return True
            return False
        except:
            return False

    async def main(self):
        await self.init()
        await self.loop()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)-10s %(message)s', level=logging.DEBUG
    )
    SpeechCloudWS.run(MyDialog, address='0.0.0.0', port=8888)
