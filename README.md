# Slack App for FIFA World Cup 2018 Bets

## Program Components

Component | Description
-- | --
[betbot.py](https://github.com/charles-wangkai/betbot_worldcup2018/blob/master/betbot.py) | The backend part to handle [Slack Slash Commands](https://api.slack.com/slash-commands).
[matches_updater.py](https://github.com/charles-wangkai/betbot_worldcup2018/blob/master/matches_updater.py) | The scheduled (crontab) task to fetch the up-to-date matches data of FIFA World Cup 2018 from [worldcup.sfg.io](http://worldcup.sfg.io), and compute the earnings for gamblers.
[Odds Graph](http://charles-wangkai.github.io/fun/world_cup_2018_odds.html?other_total=200.0&same_total=185.0) ([Source Code](https://github.com/charles-wangkai/charles-wangkai.github.io/blob/master/fun/world_cup_2018_odds.html)) | Help gamblers to get a better understanding of betting on a match result.
