from dialog import EntityMap, SpeechCloudWS, Dialog
import logging
from utils import *
import pandas as pd
from typing import Optional


class MyDialog(Dialog):
    # Attempt to use Rust-like typing to keep my sanity.
    state: State
    question: Optional[Question]
    parkhouse: Optional[ParkHouse]
    time: Optional[pd.Timestamp]
    day_of_week: Optional[DayOfWeek]
    spot_state: SpotState

    async def actually_process_text(self, text: str):
        # it"s sad that this method needs to exist like this
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
        # assume that user wants to know about available spots by default
        self.spot_state = SpotState.AVAILABLE
        # setup grammars:
        await self.define_slu_grammars(
            [
                {
                    'entity': 'numbers',
                    'data': open('./data/numbers.abnf', 'rt').read(),
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
            ]
        )
        logging.info('Finished init()')

    async def loop(self):
        logging.info('Entered loop()')
        loop = True
        while loop:
            logging.debug('new loop started')
            if self.state is State.INIT:
                logging.debug('entered INIT branch')
                # await self.synthesize_and_wait(
                #     'Dobrý den, tady informační systém pro parkovací domy Nové Divadlo a Rychtářka, můžete se ptát.'
                # )
                self.state = State.IDLE
            elif self.state is State.QUIT:
                logging.info("intered QUIT branch")
                await self.synthesize_and_wait("Nashledanou.")
                return
            elif self.state is State.HELP:
                logging.info("intered HELP branch")
                await self.synthesize_and_wait([
                    "Mluvíte s informačním systémem pro parkovací domy Nové Divadlo a Rychtářka.",
                    "Můžete se ptát na kapacitu a počty volných míst v parkovacích domech Rychářka nebo Nové Divadlo."
                ])
                self.state = State.IDLE
            if self.state is State.IDLE:
                logging.debug('entered IDLE branch')
                res = await self.actually_process_text("sedmnáct třicet")
                print('res type:', type(res.entities))
                print('res:', res.entities['numbers'])
                return
        logging.info('Finished loop()')

    def extract_timestamp(slu: EntityMap)

    async def main(self):
        await self.init()
        await self.loop()


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s %(levelname)-10s %(message)s', level=logging.DEBUG
    )
    SpeechCloudWS.run(MyDialog, address='0.0.0.0', port=8888)
