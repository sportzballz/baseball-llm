from email.mime.text import MIMEText
import requests
from bs4 import BeautifulSoup
from  common.objects import Lineup, LineupPlayer


def get_starting_lineups():
    response = requests.get('https://www.mlb.com/starting-lineups', verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')

    lineup_elements = soup.find_all("div", class_="starting-lineups__matchup")
    Lineups = []
    if len(lineup_elements) == 1:
        return Lineups
    for lineup_element in lineup_elements:
        away_team_span = lineup_element.find("span", class_="starting-lineups__team-name starting-lineups__team-name--away")
        away_team_id = away_team_span.find("a")["data-id"]
        home_team_span = lineup_element.find("span", class_="starting-lineups__team-name starting-lineups__team-name--home")
        home_team_id = home_team_span.find("a")["data-id"]
        starting_lineups = lineup_element.find("div", class_="starting-lineups__teams starting-lineups__teams--sm starting-lineups__teams--xl")
        away_lineup_class = starting_lineups.find("ol", class_="starting-lineups__team--away")
        home_lineup_class = starting_lineups.find("ol", class_="starting-lineups__team--home")
        away_players = away_lineup_class.find_all("li", class_="starting-lineups__player")
        home_players = home_lineup_class.find_all("li", class_="starting-lineups__player")
        home_lineup = []
        away_lineup = []
        home_order = 1
        away_order = 1
        for away_player in away_players:
            player_name = away_player.find("a", class_="starting-lineups__player--link").text
            player_position = away_player.find("span", class_="starting-lineups__player--position").text
            player_link = away_player.find("a", class_="starting-lineups__player--link")["href"]
            player_id= player_link.split("-")[-1]
            # away_lineup.append(LineupPlayer(int(player_id), player_name, player_position, away_order))
            away_lineup.append({"personId": int(player_id)})
            away_order += 1
            print(f"AWAY: {player_name} - {player_position} - player_id: {player_id} - team_id: {away_team_id}")
        for home_player in home_players:
            player_name = home_player.find("a", class_="starting-lineups__player--link").text
            player_position = home_player.find("span", class_="starting-lineups__player--position").text
            player_link = home_player.find("a", class_="starting-lineups__player--link")["href"]
            player_id = player_link.split("-")[-1]
            # home_lineup.append(LineupPlayer(int(player_id), player_name, player_position, home_order))
            home_lineup.append({"personId": int(player_id)})
            home_order += 1
            print(f"HOME: {player_name} - {player_position} - player_id: {player_id} - team_id: {away_team_id}")
        Lineups.append(Lineup(int(away_team_id), away_lineup))
        Lineups.append(Lineup(int(home_team_id), home_lineup))
    return Lineups

