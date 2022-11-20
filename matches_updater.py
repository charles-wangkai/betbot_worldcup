import requests

import app
from app import Bet


def set_earn(user_to_bet, winners, losers, earn_name):
    if winners and losers:
        loser_amount_sum = 0
        for loser in losers:
            loser_amount_sum += user_to_bet[loser].amount
            setattr(user_to_bet[loser], earn_name, -user_to_bet[loser].amount / 2)

        winner_amount_sum = sum(user_to_bet[winner].amount for winner in winners)

        for winner in winners:
            setattr(
                user_to_bet[winner],
                earn_name,
                loser_amount_sum * user_to_bet[winner].amount / winner_amount_sum / 2,
            )
    else:
        for bet in user_to_bet.values():
            setattr(bet, earn_name, 0)


def sign(x):
    if x < 0:
        return -1
    if x > 0:
        return 1

    return 0


if __name__ == "__main__":
    with open("matches.json", "w") as f:
        f.write(requests.get("https://worldcupjson.net/matches").text)

    for match in app.get_completed_matches():
        user_to_bet = app.read_user_to_bet(match.id)
        if any(not hasattr(bet, "score_earn") for bet in user_to_bet.values()):
            home_score = match.home_goals + int(match.home_penalties or 0)
            away_score = match.away_goals + int(match.away_penalties or 0)

            score_winners = []
            score_losers = []
            for user in user_to_bet:
                bet = user_to_bet[user]
                if bet.home_score == home_score and bet.away_score == away_score:
                    bet.score_win = True
                    score_winners.append(user)
                else:
                    bet.score_win = False
                    score_losers.append(user)
            set_earn(user_to_bet, score_winners, score_losers, "score_earn")

            outcome_winners = []
            outcome_losers = []
            for user in user_to_bet:
                bet = user_to_bet[user]
                if sign(bet.home_score - bet.away_score) == sign(
                    home_score - away_score
                ):
                    bet.outcome_win = True
                    outcome_winners.append(user)
                else:
                    bet.outcome_win = False
                    outcome_losers.append(user)
            set_earn(user_to_bet, outcome_winners, outcome_losers, "outcome_earn")

            app.write_user_to_bet(match.id, user_to_bet)
