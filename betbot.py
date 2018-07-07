#!/usr/bin/env python3

import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
from socketserver import ThreadingMixIn
import urllib.parse


VERIFICATION_TOKEN = 'k51wXw71r4wHzvImJxWyvINk'

RESULT_DRAW, RESULT_HOME, RESULT_AWAY = 'draw', 'home', 'away'

RESULT_TO_DESCRIPTION = {
    RESULT_DRAW: '预测打平',
    RESULT_HOME: '预测主队胜',
    RESULT_AWAY: '预测客队胜'
}

BET_BASE_PATH = './bet/'

COUNTRY_NAME_TO_CODE = {
    'Russia': 'ru',
    'Germany': 'de',
    'Brazil': 'br',
    'Portugal': 'pt',
    'Argentina': 'ar',
    'Belgium': 'be',
    'Poland': 'pl',
    'France': 'fr',
    'Spain': 'es',
    'Peru': 'pe',
    'Switzerland': 'ch',
    'England': 'england',
    'Colombia': 'co',
    'Mexico': 'mx',
    'Uruguay': 'uy',
    'Croatia': 'hr',
    'Denmark': 'dk',
    'Iceland': 'is',
    'Costa Rica': 'cr',
    'Sweden': 'se',
    'Tunisia': 'tn',
    'Egypt': 'eg',
    'Senegal': 'sn',
    'Iran': 'ir',
    'Serbia': 'rs',
    'Nigeria': 'ng',
    'Australia': 'au',
    'Japan': 'jp',
    'Morocco': 'ma',
    'Panama': 'pa',
    'Korea Republic': 'kr',
    'Saudi Arabia': 'sa'
}

FIFA_ID_TO_MATCH_ID = {
    '300331503': 1,
    '300353632': 2,
    '300331526': 3,
    '300331524': 4,
    '300331533': 5,
    '300331515': 6,
    '300331528': 7,
    '300331523': 8,
    '300331529': 9,
    '300331502': 10,
    '300331525': 11,
    '300331499': 12,
    '300331539': 13,
    '300331554': 14,
    '300331550': 15,
    '300331545': 16,
    '300331495': 17,
    '300331511': 18,
    '300331530': 19,
    '300331496': 20,
    '300331518': 21,
    '300331527': 22,
    '300331513': 23,
    '300331540': 24,
    '300331497': 25,
    '300340183': 26,
    '300331547': 27,
    '300331549': 28,
    '300331501': 29,
    '300331546': 30,
    '300331505': 31,
    '300331508': 32,
    '300331516': 33,
    '300331509': 34,
    '300331500': 35,
    '300340184': 36,
    '300331512': 37,
    '300331506': 38,
    '300331519': 39,
    '300331510': 40,
    '300331548': 41,
    '300331532': 42,
    '300331521': 43,
    '300331534': 44,
    '300331507': 45,
    '300331553': 46,
    '300331520': 47,
    '300340182': 48,
    '300331537': 49,
    '300331544': 50,
    '300331517': 51,
    '300331498': 52,
    '300331535': 53,
    '300331551': 54,
    '300331514': 55,
    '300331542': 56,
    '300331543': 57,
    '300331538': 58,
    '300331541': 59,
    '300331504': 60,
    '300331531': 61,
    '300331522': 62,
    '300331536': 63,
    '300331552': 64
}


def compare(home_score, away_score):
    if home_score == away_score:
        return RESULT_DRAW
    elif home_score > away_score:
        return RESULT_HOME
    else:
        return RESULT_AWAY


class Match:
    def __init__(self, match_id, status, time, stage_name, dt_str, home, away, home_goals, away_goals, home_penalties, away_penalties):
        self.match_id = match_id
        self.status = status
        self.time = time
        self.stage_name = stage_name
        self.dt = datetime.datetime.strptime(
            dt_str[:-1] + '+0000', '%Y-%m-%dT%H:%M:%S%z')
        self.home = home
        self.away = away
        self.home_goals = home_goals
        self.away_goals = away_goals
        self.home_penalties = home_penalties
        self.away_penalties = away_penalties

    def is_knockout(self):
        return self.match_id >= 49

    def is_completed(self):
        return self.status == 'completed' or self.time == 'full-time'

    def is_penalty_resolved(self):
        return self.home_penalties > 0 or self.away_penalties > 0

    def get_dt_str_in_beijing_time(self):
        return self.dt.astimezone(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')

    def get_actual_result(self):
        return compare(self.home_penalties, self.away_penalties) if self.is_penalty_resolved() else compare(self.home_goals, self.away_goals)


def read_matches():
    matches = []
    for entry in json.loads(open('matches.json').read()):
        matches.append(Match(FIFA_ID_TO_MATCH_ID[entry['fifa_id']],
                             entry['status'],
                             entry['time'],
                             entry['stage_name'],
                             entry['datetime'],
                             entry['home_team']['country'],
                             entry['away_team']['country'],
                             entry['home_team'].get('goals'),
                             entry['away_team'].get('goals'),
                             entry['home_team'].get('penalties'),
                             entry['away_team'].get('penalties')))

    matches.sort(key=lambda match: match.match_id)
    return matches


def get_current_matches():
    return [match for match in read_matches()
            if datetime.datetime.now(datetime.timezone.utc) < match.dt
            and 'To Be Determined' not in [match.home, match.away]]


def get_completed_matches():
    return [match for match in read_matches()[::-1] if match.is_completed()]


def build_bet_path(match_id):
    return os.path.join(BET_BASE_PATH, str(match_id) + '.json')


def read_bets(match_id):
    bet_path = build_bet_path(match_id)

    return json.loads(open(bet_path).read()) if os.path.exists(bet_path) else {}


def write_bets(match_id, bets):
    with open(build_bet_path(match_id), 'w') as f:
        f.write(json.dumps(bets))


def compute_other_total(bets, target_result):
    return sum([bets[result][user]['amount']
                for result in bets if result != target_result
                for user in bets[result]])


def compute_same_total(bets, target_result):
    return sum([bets[result][user]['amount']
                for result in bets if result == target_result
                for user in bets[result]])


def round_amount(amount):
    return round(amount, 2)


def build_bet_str(user, entry):
    bet_str = '{}: 押 {:g} 元'.format(user, round_amount(entry['amount']))
    if 'earn' in entry:
        bet_str += ' (赚赔 {:+g} 元)'.format(round_amount(entry['earn']))
    return bet_str


def build_bet_detail(bets, result):
    if result in bets and bets[result]:
        return ', '.join([build_bet_str(user, bets[result][user]) for user in bets[result]])
    else:
        return '无人'


def build_odds(match, bets, result):
    return '<http://charles-wangkai.github.io/fun/world_cup_2018_odds.html?other_total={}&same_total={}|{}赔率>'.format(
        compute_other_total(bets, result),
        compute_same_total(bets, result),
        '最终' if match.is_completed() else '当前')


def build_field_title(match, result, bets):
    if match.is_completed():
        return '{} {} (共押 {:g} 元)'.format(
            '✅' if result == match.get_actual_result() else '❌',
            RESULT_TO_DESCRIPTION[result],
            round_amount(compute_same_total(bets, result)))
    else:
        return '{} (共押 {:g} 元)'.format(
            RESULT_TO_DESCRIPTION[result],
            round_amount(compute_same_total(bets, result)))


def build_fields(match):
    bets = read_bets(match.match_id)

    results = ([] if match.is_knockout() else [RESULT_DRAW]) + \
        [RESULT_HOME, RESULT_AWAY]
    return [{'title': build_field_title(match, result, bets),
             'value': '{}\n{}'.format(build_odds(match, bets, result), build_bet_detail(bets, result)),
             'short': False}
            for result in results]


def build_country_str(country_name, reverse_order=False):
    output_format_fields = [':flag-{code}:', '`{country_name}`']

    if reverse_order:
        output_format_fields = output_format_fields[::-1]

    return ' '.join(output_format_fields).format(code=COUNTRY_NAME_TO_CODE[country_name], country_name=country_name)


def build_match_str(match):
    if match.is_completed():
        if match.is_penalty_resolved():
            return '*{}*: ({}) [{}] {} {} ({}) - ({}) {} {}'.format(
                match.match_id,
                match.stage_name,
                match.get_dt_str_in_beijing_time(),
                build_country_str(
                    match.home, True),
                match.home_goals,
                match.home_penalties,
                match.away_penalties,
                match.away_goals,
                build_country_str(match.away))
        else:
            return '*{}*: ({}) [{}] {} {} - {} {}'.format(
                match.match_id,
                match.stage_name,
                match.get_dt_str_in_beijing_time(),
                build_country_str(
                    match.home, True),
                match.home_goals,
                match.away_goals,
                build_country_str(match.away))
    else:
        return '*{}*: ({}) [{}] {} vs {}'.format(
            match.match_id,
            match.stage_name,
            match.get_dt_str_in_beijing_time(),
            build_country_str(
                match.home, True),
            build_country_str(match.away))


def build_result_str(match, result):
    if result == RESULT_DRAW:
        return '预测打平'
    elif result == RESULT_HOME:
        return '预测主队 {} 胜'.format(build_country_str(match.home))
    elif result == RESULT_AWAY:
        return '预测客队 {} 胜'.format(build_country_str(match.away))


def parse_bet_parameters(text):
    if not text:
        return None

    parts = text.split()
    if len(parts) != 3:
        return None

    match_id_str, result, amount_str = parts
    try:
        match_id = int(match_id_str)
        amount = round_amount(float(amount_str))
    except ValueError:
        return None

    matches = [match for match in get_current_matches()
               if match.match_id == match_id]
    if not matches:
        return None
    match = matches[0]

    if result not in [RESULT_HOME, RESULT_AWAY] and (result != RESULT_DRAW or match.is_knockout()):
        return None

    if amount != 0 and amount < 10:
        return None

    return [match, result, amount]


def get_value(query, key):
    if key in query and query[key]:
        return query[key][0]
    return None


class SlackRequestHandler(BaseHTTPRequestHandler):
    def respond(self, resp):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(resp).encode())

    def do_POST(self):
        query = urllib.parse.parse_qs(self.rfile.read(
            int(self.headers['content-length'])).decode())
        logging.debug('query: {}'.format(query))

        if get_value(query, 'token') != VERIFICATION_TOKEN:
            return

        if self.path == '/about':
            resp = {
                'response_type': 'in_channel',
                'text': '\n'.join([
                    '欢迎参与世界杯竞猜 (百观版) ！',
                    '- 你可以对还未开始的比赛进行投注 (投注会在比赛开始时关闭)。',
                    '- 对每场比赛只竞猜最终的赛果 (小组赛每场有胜平负，淘汰赛每场只有胜负)。',
                    '- *猜对方将按照投注金额比例分配赢取猜错方的总投注资金，所以本竞猜为“零和游戏”，是无法共同致富的，切记！*',
                    '- 在比赛开始前可以多次更改投注，以最后一次为准。',
                    '- 可以投注一场比赛的多种赛果，以达到对冲的作用。',
                    '- 所有的资金结算将在整个世界杯所有比赛结束后各个玩家间通过线下完成，期间这里只进行记账。',
                    '- 投注需通过输入指令完成，格式为 `/bet <场次号> <预测赛果> <金额>`。其中，<场次号> 可通过指令 `/current` 查询；<预测赛果> 取值为: draw 代表 打平 (只适用于小组赛), home 代表 主队胜, away 代表 客队胜；<金额> 单位为人民币的元，有效范围为非负数，支持小数，输入 0 可撤销之前的押注。',
                    '- 投注举例: 假设下注决赛比赛中的客队获胜并押 19 块 5 毛钱，输入指令 `/bet 64 away 19.5` 即可。',
                    '- *进入淘汰赛阶段后，所有比赛的单次下注金额至少为 10 元。*',
                    '- 其它的指令还包括: `/current`, `/history`, `/balance`',
                    '- 如有任何问题，欢迎在此 channel 里讨论。',
                    '',
                    '最后，请牢记:',
                    '*小赌怡情，大赌伤身！* :slightly_smiling_face:'
                ])
            }
        elif self.path == '/current':
            resp = {
                'response_type': 'in_channel',
                'text': '当前可以下注的比赛: (格式为 <场次号>: (<阶段>) [<比赛时间>] <主队> vs <客队>)',
                'attachments': [{
                    'text': build_match_str(match),
                    'fields': build_fields(match),
                    'mrkdwn_in': ['text', 'fields']
                }
                    for match in get_current_matches()]
            }
        elif self.path == '/history':
            resp = {
                'response_type': 'in_channel',
                'text': '已完结的比赛:',
                'attachments': [{
                    'text': build_match_str(match),
                    'fields': build_fields(match),
                    'mrkdwn_in': ['text', 'fields']
                }
                    for match in get_completed_matches()]
            }
        elif self.path == '/balance':
            user_to_balance = {}
            for match in get_completed_matches():
                for result_bets in read_bets(match.match_id).values():
                    for user in result_bets:
                        user_to_balance[user] = user_to_balance.get(user, 0) + \
                            result_bets[user]['earn']

            balance_and_user_list = sorted(
                [(user_to_balance[user], user) for user in user_to_balance])[::-1]

            resp = {
                'response_type': 'in_channel',
                'text': '总账目列表:',
                'attachments': [{
                    'text': '\n'.join(['{}: {:+g} 元'.format(balance_and_user[1], round_amount(balance_and_user[0]))
                                       for balance_and_user in balance_and_user_list])
                }]
            }
        elif self.path == '/bet':
            bet_parameters = parse_bet_parameters(
                get_value(query, 'text'))

            if bet_parameters:
                match, result, amount = bet_parameters
                user = get_value(query, 'user_name')

                bets = read_bets(match.match_id)
                if result not in bets:
                    bets[result] = {}

                if amount > 0:
                    bets[result][user] = {'amount': amount}

                    resp = {
                        'response_type': 'in_channel',
                        'text': '{}，你已成功对比赛 {} 下注 {}，并押 {:g} 元！'.format(
                            user,
                            build_match_str(match),
                            build_result_str(match, result),
                            amount)
                    }
                else:
                    if user in bets[result]:
                        bets[result].pop(user)

                        resp = {
                            'response_type': 'in_channel',
                            'text': '{}，你已撤销对比赛 {} 的 {} 的下注！'.format(
                                user,
                                build_match_str(match),
                                build_result_str(match, result))
                        }
                    else:
                        resp = {
                            'response_type': 'in_channel',
                            'text': '{}，你之前没有对比赛 {} 的 {} 的结果下过注，请重试！'.format(
                                user,
                                build_match_str(match),
                                build_result_str(match, result))
                        }

                write_bets(match.match_id, bets)
            else:
                resp = {
                    'response_type': 'in_channel',
                    'text': '参数错误，请重试！(格式为 `/bet <场次号> <预测赛果> <金额>`，并请再次检查各参数的取值是否有错误，比如 <金额> 必须等于 0 或者大于等于 10)'
                }

        self.respond(resp)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    pass


def run_server():
    server = ThreadedHTTPServer(('', 9018), SlackRequestHandler)
    logging.info('Server starts at {}:{}'.format(*server.server_address))
    server.serve_forever()


def config_log():
    logging.basicConfig(
        format='[%(asctime)s] %(levelname)s - %(message)s', level='NOTSET')


if __name__ == '__main__':
    config_log()
    run_server()
