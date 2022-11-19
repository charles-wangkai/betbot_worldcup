import datetime
import json
import logging
import os

import jsonpickle
from slack_bolt import App

BETS_BASE_PATH = "./bets/"

COUNTRY_NAME_TO_CODE = {
    "Qatar": "qa",
    "Ecuador": "ec",
    "Senegal": "sn",
    "Netherlands": "nl",
    "England": "england",
    "Iran": "ir",
    "Wales": "wales",
    "United States": "us",
    "Argentina": "ar",
    "Saudi Arabia": "sa",
    "Mexico": "mx",
    "Poland": "pl",
    "France": "fr",
    "Denmark": "dk",
    "Tunisia": "tn",
    "Australia": "au",
    "Spain": "es",
    "Germany": "de",
    "Japan": "jp",
    "Costa Rica": "cr",
    "Belgium": "be",
    "Canada": "ca",
    "Morocco": "ma",
    "Croatia": "hr",
    "Brazil": "br",
    "Serbia": "rs",
    "Switzerland": "ch",
    "Cameroon": "cm",
    "Portugal": "pt",
    "Ghana": "gh",
    "Uruguay": "uy",
    "Korea Republic": "kr",
}

app = App()


@app.command("/about")
def about(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    respond(
        response_type="in_channel",
        text="""欢迎参与世界杯竞猜游戏！
- 您可以对还未开始的比赛进行投注 (投注会在比赛开始时关闭)。
- 您可以对每场比赛竞猜一个比分，该比分将会同时用于两种竞猜用途: “精确比分”、“胜负关系”。
- “精确比分”: 完全猜中准确的比分算赢，其它算输。
- ”胜负关系“: 竞猜的比分只要在胜负关系上是对的即可算赢，其它算输。例如，您竞猜的比分是 2 - 1，实际的赛果是 3 - 0，虽然比分上不完全一致，但是在胜负关系上仍然是算您猜对的。
- 您投注的总金额将 50% 用于 “精确比分”，50% 用于 “胜负关系”。
- 您竞猜的比分将是整场比赛的总比分，如果比赛由点球决战决出胜负，点球决战阶段的进球数也是包括进去的。例如，一场比赛常规时间的比分是 2 - 2，点球决战的比分是 4 - 5，那么您应该竞猜 6 - 7 才算赢得了 “精确比分”。
- *猜对方将按照投注金额的比例共同赢取猜错方的总投注资金，所以本竞猜为“零和游戏”，是无法共同致富的。*
- 在比赛开始前可以多次更改投注，以最后一次为准。
- 所有的资金结算将在整个世界杯所有比赛结束后各个玩家间通过线下完成，期间这里只进行记账。
- 投注需通过输入指令完成，格式为 `/bet <场次号> <主队比分> <客队比分> <金额>`。其中，<场次号> 可通过指令 `/current` 查询到；<金额> 单位为人民币的元，必须是整数。
- 投注举例: 假设下注最终决赛比赛中的比分是 2 - 4 并押 50 元，则输入指令 `/bet 64 2 4 50` 即可。
- 所有比赛的单次下注金额至少为 20 元。
- 其它的指令还包括: `/current`, `/history`, `/balance`, `/cancel <场次号>`
- 如有任何问题，欢迎在此 channel 里讨论。

最后，请牢记:
*小赌怡情，大赌伤身！* :slightly_smiling_face:""",
    )


@app.command("/current")
def current(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    respond(
        response_type="in_channel",
        text="当前可以下注的比赛: (格式为 <场次号>: (<阶段>) [<比赛时间>] <主队> vs <客队>)",
        attachments=[
            {
                "text": build_match_str(match),
                "fields": build_fields(match),
                "mrkdwn_in": ["text", "fields"],
            }
            for match in get_current_matches()
        ],
    )


@app.command("/history")
def history(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    respond(
        response_type="in_channel",
        text="已结束的比赛:",
        attachments=[
            {
                "text": build_match_str(match),
                "fields": build_fields(match),
                "mrkdwn_in": ["text", "fields"],
            }
            for match in get_completed_matches()
        ],
    )


@app.command("/balance")
def balance(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    user_to_balance = {}
    for match in get_completed_matches():
        user_to_bet = read_user_to_bet(match.id)
        for user in user_to_bet:
            bet = user_to_bet[user]
            user_to_balance[user] = (
                user_to_balance.get(user, 0) + bet.score_earn + bet.outcome_earn
            )

    respond(
        response_type="in_channel",
        text="总账目列表:",
        attachments=[
            {"text": f"{user}: {user_to_balance[user]:.2f} 元"}
            for user in sorted(
                user_to_balance, key=lambda user: user_to_balance[user], reverse=True
            )
        ],
    )


@app.command("/bet")
def bet(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    bet_parameters = parse_bet_parameters(body.get("text", ""))
    if bet_parameters:
        match, home_score, away_score, amount = bet_parameters
        user = body["user_name"]

        user_to_bet = read_user_to_bet(match.id)
        user_to_bet[user] = Bet(home_score, away_score, amount)
        write_user_to_bet(match.id, user_to_bet)

        response_text = f"{user}，您已成功对比赛 {build_match_str(match)} 竞猜比分 *{home_score} - {away_score}* ，并押 *{amount}* 元！"
    else:
        response_text = "参数错误，请重试！(格式为 `/bet <场次号> <主队比分> <客队比分> <金额>`，请再次检查参数的取值是否有错误，比如 <金额> 必须是大于等于 20 的整数；再比如由于淘汰赛阶段的比赛不存在平局结果，因此相同的 <主队比分> 和 <客队比分> 在淘汰赛阶段是肯定不可能发生的)"

    respond(response_type="in_channel", text=response_text)


@app.command("/cancel")
def cancel(ack, body, respond):
    logging.info(f"{body = }")
    ack(response_type="in_channel")

    match = parse_cancel_parameters(body.get("text", ""))
    if match:
        user = body["user_name"]

        user_to_bet = read_user_to_bet(match.id)
        if user in user_to_bet:
            user_to_bet.pop(user)
            write_user_to_bet(match.id, user_to_bet)

            response_text = f"{user}，您已成功取消对比赛 {build_match_str(match)} 的竞猜！"
        else:
            response_text = f"{user}，您之前没有对比赛 {build_match_str(match)} 进行过竞猜，请重试！"
    else:
        response_text = "参数错误，请重试！(格式为 `/cancel <场次号>`，请再次检查参数的取值是否有错误)"

    respond(response_type="in_channel", text=response_text)


def parse_cancel_parameters(text):
    parts = text.split()
    if len(parts) != 1:
        return None

    (match_id_str,) = parts
    try:
        match_id = int(match_id_str)
    except ValueError:
        return None

    match = find_match(match_id)

    return match


def parse_bet_parameters(text):
    parts = text.split()
    if len(parts) != 4:
        return None

    match_id_str, home_score_str, away_score_str, amount_str = parts
    try:
        match_id = int(match_id_str)
        home_score = int(home_score_str)
        away_score = int(away_score_str)
        amount = int(amount_str)
    except ValueError:
        return None

    match = find_match(match_id)

    if (
        home_score < 0
        or away_score < 0
        or (match.is_knockout() and home_score == away_score)
    ):
        return None

    if amount < 20:
        return None

    return match, home_score, away_score, amount


def find_match(match_id):
    matches = [match for match in get_current_matches() if match.id == match_id]

    return matches[0] if matches else None


def build_fields(match):
    user_to_bet = read_user_to_bet(match.id)

    return [
        {
            "title": user,
            "value": str(user_to_bet[user]),
        }
        for user in user_to_bet
    ]


def read_user_to_bet(match_id):
    bet_path = build_bet_path(match_id)

    return jsonpickle.decode(open(bet_path).read()) if os.path.exists(bet_path) else {}


def write_user_to_bet(match_id, user_to_bet):
    with open(build_bet_path(match_id), "w") as f:
        f.write(jsonpickle.encode(user_to_bet))


def build_bet_path(match_id):
    return os.path.join(BETS_BASE_PATH, str(match_id) + ".json")


class Bet:
    def __init__(self, home_score, away_score, amount):
        self.home_score = home_score
        self.away_score = away_score
        self.amount = amount

    def __str__(self):
        result = f"竞猜比分 {self.home_score} - {self.away_score}, 押 {self.amount} 元"
        if hasattr(self, "score_earn"):
            score_earn_str = "精确比分 " + (
                f":white_check_mark: : 赚 {self.score_earn:.2f} 元"
                if self.score_earn >= 0
                else f":x: : 赔 {-self.score_earn:.2f} 元"
            )
            outcome_earn_str = "胜负关系 " + (
                f":white_check_mark: : 赚 {self.outcome_earn:.2f} 元"
                if self.outcome_earn >= 0
                else f":x: : 赔 {-self.outcome_earn:.2f} 元"
            )
            result += f"\n{score_earn_str}, {outcome_earn_str}"

        return result


def build_match_str(match):
    template = "*{match_id}*: ({stage_name}) [{dt}] "
    if match.is_completed():
        if match.is_penalty_resolved():
            template += "{home_name} {home_flag} {home_goals} ({home_penalties}) - ({away_penalties}) {away_goals} {away_flag} {away_name}"
        else:
            template += "{home_name} {home_flag} {home_goals} - {away_goals} {away_flag} {away_name}"
    else:
        template += "{home_name} {home_flag} vs {away_flag} {away_name}"

    return template.format(
        match_id=match.id,
        stage_name=match.stage_name,
        dt=match.get_dt_str_in_beijing_time(),
        home_name=f"`{match.home_name}`",
        home_flag=f":flag-{COUNTRY_NAME_TO_CODE[match.home_name]}:",
        home_goals=match.home_goals,
        home_penalties=match.home_penalties,
        away_name=f"`{match.away_name}`",
        away_flag=f":flag-{COUNTRY_NAME_TO_CODE[match.away_name]}:",
        away_goals=match.away_goals,
        away_penalties=match.away_penalties,
    )


def read_matches():
    return sorted(
        [
            Match(
                entry["id"],
                entry["status"],
                entry["stage_name"],
                entry["datetime"],
                entry["home_team"]["name"],
                entry["home_team"].get("goals"),
                entry["home_team"].get("penalties"),
                entry["away_team"]["name"],
                entry["away_team"].get("goals"),
                entry["away_team"].get("penalties"),
            )
            for entry in json.loads(open("matches.json").read())
        ],
        key=lambda match: match.id,
    )


def get_current_matches():
    return [
        match
        for match in read_matches()
        if datetime.datetime.now(datetime.timezone.utc) < match.dt
        and "To Be Determined" not in [match.home_name, match.away_name]
    ]


def get_completed_matches():
    return [match for match in read_matches()[::-1] if match.is_completed()]


class Match:
    def __init__(
        self,
        id,
        status,
        stage_name,
        dt_str,
        home_name,
        home_goals,
        home_penalties,
        away_name,
        away_goals,
        away_penalties,
    ):
        self.id = id
        self.status = status
        self.stage_name = stage_name
        self.dt = datetime.datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
        self.home_name = home_name
        self.home_goals = home_goals
        self.home_penalties = home_penalties
        self.away_name = away_name
        self.away_goals = away_goals
        self.away_penalties = away_penalties

    def is_knockout(self):
        return self.id >= 49

    def is_completed(self):
        return self.status == "completed"

    def is_penalty_resolved(self):
        return self.home_penalties is not None

    def get_dt_str_in_beijing_time(self):
        return self.dt.astimezone(
            datetime.timezone(datetime.timedelta(hours=8))
        ).strftime("%Y-%m-%d %H:%M")


if __name__ == "__main__":
    logging.basicConfig(
        format="[%(asctime)s] %(levelname)s - %(message)s", level=logging.INFO
    )

    app.start(3000)
