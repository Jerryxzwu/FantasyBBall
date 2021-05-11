from nba_api.stats.endpoints import playergamelog, playernextngames
from nba_api.stats.static import players

from datetime import date, timedelta
import calendar

from collections import defaultdict

month_str_to_int = {month.upper():index for index,month in enumerate(calendar.month_abbr) if month}


class NBAData():

	CAT = {'FGM','FGA','FTM','FTA','PTS','FG3M','REB','AST','STL','BLK','TOV'}

	def __init__(self, roster):
		self.roster = {}
		for player_name in roster:
			player_info = players.find_players_by_full_name(player_name)
			if len(player_info) > 1:
				error_message = 'More than one NBA player has the name of' + player_name
				raise RuntimeError(error_message)
			elif len(player_info) == 0:
				print('NBA endpoints does not have data on ' + player_name)
				continue
			player_info = player_info[0]
			self.roster[player_name] = player_info['id']
		self.roster_data = self.roster_cat_data()

	def individual_cat_data(self,player_id):
		raw_game_log = playergamelog.PlayerGameLog(player_id).player_game_log.get_dict()
		headers = raw_game_log['headers']
		by_game_raw = raw_game_log['data']
		by_cat_raw = list(zip(*by_game_raw))
		by_cat_labeled = {}
		for i in range(len(headers)):
			curr_cat = headers[i]
			if curr_cat in self.CAT:
				by_cat_labeled[curr_cat] = by_cat_raw[i]
			elif curr_cat == 'GAME_DATE':
				by_cat_labeled[curr_cat] = [self._str_to_date(date_str) for date_str in by_cat_raw[i]]
		return by_cat_labeled

	def roster_cat_data(self):
		roster_by_cat = {}
		for player_name, player_id in self.roster.items():
			player_data = self.individual_cat_data(player_id)
			roster_by_cat[player_name] = player_data
		return roster_by_cat

	def player_cat_avg(self,player_name,num_game):
		cat_avg = {}
		for cat in self.CAT:
			cat_avg[cat] = sum(self.roster_data[player_name][cat][:num_game])/num_game
		return cat_avg

	def roster_cat_total(self,num_game=5):
		agg_cat_total = defaultdict(float)
		for player_name, player_id in self.roster.items():
			ply_cat_avg = self.player_cat_avg(player_name,num_game)
			ply_games_left = self.games_left_this_week(player_id)
			for cat in self.CAT:
				agg_cat_total[cat] += ply_cat_avg[cat]*ply_games_left
		agg_cat_total['FG%'] = agg_cat_total['FGM']/agg_cat_total['FGA']
		agg_cat_total['FT%'] = agg_cat_total['FTM']/agg_cat_total['FTA']
		return agg_cat_total

	#Expecting "Month_name Day_number, Year_number" in string format, returns date object
	def _str_to_date(self, date_str):
		date_str = date_str.replace(',','')
		date_str_lst = date_str.split()

		year = int(date_str_lst[2])
		month = month_str_to_int[date_str_lst[0]]
		day = int(date_str_lst[1])

		return date(year,month,day)

	def _next_monday(self):
		today = date.today()
		days_to_next_monday = 7-today.weekday()
		return today+timedelta(days = days_to_next_monday)


	def individual_future_games(self,player_id):
		future_games = playernextngames.PlayerNextNGames(player_id).next_n_games.get_dict()
		date_index = future_games['headers'].index('GAME_DATE')
		future_games_dates = list(zip(*future_games['data']))[date_index]
		return future_games_dates

	def games_left_this_week(self,player_id):
		res = 0
		end_date = self._next_monday()
		for date_str in self.individual_future_games(player_id):
			gdate = self._str_to_date(date_str)
			if gdate < end_date:
				res += 1
				continue
			break
		return res
