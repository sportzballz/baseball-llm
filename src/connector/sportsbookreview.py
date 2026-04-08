import json
import time
from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from  common.objects import Lineup, LineupPlayer


def get_odds_by_date(date):
    response = requests.get(f'https://www.sportsbookreview.com/betting-odds/mlb-baseball/?date={date}')
    soup = BeautifulSoup(response.text, 'html.parser')
    daily_odds_json_str = soup.find("script", id="__NEXT_DATA__").text
    text_file = open(f'resources/odds/{date}.json', "w")
    text_file.write(daily_odds_json_str)
    text_file.close()
    time.sleep(1)

    # daily_odds_json = json.loads(daily_odds_json_str)
    # print(daily_odds_json)
    # for lineup_element in lineup_elements:
    #     odds_span = lineup_element.find("script", id="__NEXT_DATA__")
    #     print(odds_span.text)
    #     odds_span_a = lineup_element.find("span", class_="GameRows_gradientContainer__ZajIf")
    #     print(odds_span_a)
    # Lineups = []

