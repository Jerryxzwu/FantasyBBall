from yahoo_oauth import OAuth2

import yahoo_fantasy_api as yfa


class YahooFantasyData:

	def __init__(self, client_secret):
		self.sc = OAuth2(None,None,from_file=client_secret)
		
		self.gm = yfa.Game(self.sc,'nba')

		league_id = self.gm.league_ids()[-1]
		self.lg = self.gm.to_league(league_id)

		self.tm = self.get_team()

	def get_team(self,team_key=None):
		if team_key == None:
			team_key = self.lg.team_key()
		tm = self.lg.to_team(team_key)
		return tm

	def _get_matchup(self):
		curr_week = self.lg.current_week()
		opp_id = self.tm.matchup(curr_week)
		opp_tm = self.lg.to_team(opp_id)
		return opp_tm

	def get_yahoo_roster(self,team):
		roster = team.roster()
		return roster

	#Returns a list of non-injured players' names on team
	def get_simple_roster(self,team):
		def isInjured(player):
			return 'IL' in player['eligible_positions']
		abbr_change = {'GS':'GSW','NO':'NOP','NY':'NYK','SA':'SAS'}
		def teamAbbrConverter(abbr):
			if abbr in abbr_change:
				abbr = abbr_change[abbr]
			return abbr
		yahoo_roster = self.get_yahoo_roster(team)
		name_roster = [player['name'] for player in yahoo_roster if not isInjured(player)]
		name_nba_team_roster = []
		for name in name_roster:
			nba_team = self.lg.player_details(name)[0]['editorial_team_abbr'].upper()
			nba_team = teamAbbrConverter(nba_team)
			name_nba_team_roster.append((name,nba_team))
		return name_nba_team_roster

	def get_own_roster(self):
		return self.get_simple_roster(self.tm)

	def get_opp_roster(self):
		return self.get_simple_roster(self._get_matchup())