#!/usr/bin/env python3

import requests

import betbot


def is_settled(bets):
    for result in bets:
        for user in bets[result]:
            if 'earn' not in bets[result][user]:
                return False
    return True


if __name__ == '__main__':
    session = requests.Session()
    session.mount('http://', requests.adapters.HTTPAdapter(max_retries=3))
    resp = session.get('http://worldcup.sfg.io/matches').text

    with open('matches.json', 'w') as f:
        f.write(resp)

    for match in betbot.get_completed_matches():
        bets = betbot.read_bets(match.match_id)

        if not is_settled(bets):
            actual_result = match.get_actual_result()

            bet_total = 0
            winning_total = 0
            for result in bets:
                for user in bets[result]:
                    amount = bets[result][user]['amount']

                    if result == actual_result:
                        bet_total += amount
                    else:
                        winning_total += amount

            if bet_total > 0 and winning_total > 0:
                for result in bets:
                    for user in bets[result]:
                        entry = bets[result][user]

                        if result == actual_result:
                            entry['earn'] = winning_total * \
                                entry['amount'] / bet_total
                        else:
                            entry['earn'] = -entry['amount']
            else:
                for result in bets:
                    for user in bets[result]:
                        bets[result][user]['earn'] = 0

            betbot.write_bets(match.match_id, bets)
