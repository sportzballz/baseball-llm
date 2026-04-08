import os

import pytz
from slack_sdk import WebClient
from datetime import datetime


def post_backtest(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post_todays_pick(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    if not is_already_posted("todays-pick"):
        client.chat_postMessage(channel=f"#todays-pick", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post_todays_pick_backtest(msg: str, model: str, pick_won="none"):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    # if not is_already_posted("todays-pick-backtest"):
    client.chat_postMessage(channel=f"#todays-pick-backtest", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')


def post(msg: str, model: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#{model}-model", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')
    hour = datetime.now(pytz.timezone('US/Eastern')).strftime("%H")
    # post todays-picks at 5pm
    print(f'Hour is: {hour}')
    if hour == "17":
        print(f'Posting #todays-picks')
        client.chat_postMessage(channel=f"#todays-picks", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')

def post_sportzballz(msg: str):
    print(f'Posting #daily-results')
    client = WebClient(token=os.environ['SPORTZBALLZ_SLACK_TOKEN'])
    client.chat_postMessage(channel=f"#todays-picks", text=msg, icon_emoji=':sportzballz:', username='sportzballz')
    hour = datetime.now(pytz.timezone('US/Eastern')).strftime("%H")
    # post todays-picks at 5pm
    print(f'Hour is: {hour}')
    if hour == "12":
        print(f'Posting #daily-results')
        client.chat_postMessage(channel=f"#daily-results", text=msg, icon_emoji=':sportzballz:', username='SportzBallz')
        if '```+' == msg[:4]:
            client.chat_postMessage(channel=f"#plus-money-picks", text=msg, icon_emoji=':sportzballz:',
                                    username='sportzballz')


def _get_channel_id(client: WebClient, channel_name: str):
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel,private_channel",
            limit=500,
            cursor=cursor,
        )
        for ch in resp.get("channels", []):
            if ch.get("name") == channel_name:
                return ch.get("id")
        cursor = resp.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            return None


def _is_today_est(ts: str):
    try:
        msg_dt = datetime.fromtimestamp(float(ts), tz=pytz.timezone("US/Eastern"))
        today = datetime.now(pytz.timezone("US/Eastern")).date()
        return msg_dt.date() == today
    except Exception:
        return False


def refresh_plus_money_picks(msg: str):
    """
    Replace today's plus-money post in #plus-money-picks, then post latest.
    """
    client = WebClient(token=os.environ["SPORTZBALLZ_SLACK_TOKEN"])
    channel_name = "plus-money-picks"
    channel_id = _get_channel_id(client, channel_name)
    if not channel_id:
        print(f"Could not find Slack channel #{channel_name}")
        return

    marker = "PLUS_MONEY_DAILY"

    # Delete today's prior marker posts (best effort)
    cursor = None
    while True:
        hist = client.conversations_history(channel=channel_id, limit=200, cursor=cursor)
        messages = hist.get("messages", [])
        for m in messages:
            text = m.get("text", "")
            ts = m.get("ts")
            if not ts:
                continue
            if _is_today_est(ts) and marker in text:
                # Do not remove prior plus-money post if it contains started-game markers.
                # In this codebase, "$" is applied once live score context is present.
                if "$" in text:
                    continue
                try:
                    client.chat_delete(channel=channel_id, ts=ts)
                except Exception as e:
                    print(f"Could not delete old plus-money post ts={ts}: {e}")
        cursor = hist.get("response_metadata", {}).get("next_cursor")
        if not cursor:
            break

    stamped = datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %I:%M %p %Z")
    final_msg = f"[{marker}]\n{msg}\n\nUpdated: {stamped}"
    client.chat_postMessage(
        channel=f"#{channel_name}",
        text=final_msg,
        icon_emoji=":sportzballz:",
        username="sportzballz",
    )

def is_already_posted(target_channel: str):
    client = WebClient(token=os.environ['SLACK_TOKEN'])
    response = client.conversations_list()
    channels = response["channels"]
    already_posted = False
    for channel in channels:
        if channel["name"] == target_channel:
            id = channel["id"]
            response = client.conversations_history(channel=id)
            latest_msg = response["messages"][0]
            # print(latest_msg)
            d = datetime.fromtimestamp(int(latest_msg["ts"].split(".")[0])).strftime("%m-%d-%Y")
            today = datetime.now(pytz.timezone('US/Eastern')).strftime("%m-%d-%Y")
            if d == today:
                already_posted=True
    return already_posted
