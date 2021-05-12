from nba_api.stats.endpoints import playergamelog, playernextngames, commonallplayers

from datetime import date, timedelta
import calendar

from collections import defaultdict

import pandas as pd 
import numpy as np

month_str_to_int = {month.upper():index for index,month in enumerate(calendar.month_abbr) if month}


class PlayersInfo():

	def __init__(self):
		self.players_info = self.get_active_players_info()

	def get_active_players_info(self):
		endpoint_obj = commonallplayers.CommonAllPlayers(is_only_current_season=1)
		endpoint_info = endpoint_obj.common_all_players.get_dict()
		endpoint_headers = endpoint_info['headers']
		endpoint_data = endpoint_info['data']

		#Use of last_comma_first is the least ambiguous way to determine
		#a player's first name and last name

		id_index = endpoint_headers.index('PERSON_ID')
		team_index = endpoint_headers.index('TEAM_ABBREVIATION')
		last_first_index = endpoint_headers.index('DISPLAY_LAST_COMMA_FIRST')
		
		full_lst, first_lst, last_lst, team_lst, id_lst = [],[],[],[],[]

		for player_info in endpoint_data:
			last_comma_first_name = player_info[last_first_index]
			#Perhaps raise an exception when comma appears more than once
			lastname, firstname = last_comma_first_name.split(', ')
			fullname = firstname + ' ' + lastname
			team_abbr = player_info[team_index]
			player_id = player_info[id_index]

			full_lst.append(fullname)
			first_lst.append(firstname)
			last_lst.append(lastname)
			team_lst.append(team_abbr)
			id_lst.append(player_id)

		df = pd.DataFrame({
				'full_name':full_lst,
				'first_name':first_lst,
				'last_name':last_lst,
				'team':team_lst,
				'id':id_lst
			})

		return df

	def get_player_id(self, yname, team):
		df = self.players_info
		#f0_df stands for first iteration of filtered df 
		f0_df = df[df['full_name']==yname]
		#len(filter_df) is not expected to be >1 since that implies two NBA players
		#have the exact same names
		if len(f0_df) == 1:
			return f0_df['id'].iloc[0]

		#else no match on full name

		firstname, lastname = yname.split(' ',1)
		f1_df = df[df['last_name']==lastname]
		if len(f1_df) == 0:
			raise RuntimeError('Cannot find '+yname+' in NBA endpoint data')
		elif len(f1_df) == 1:
			return f1_df['id'].iloc[0]

		f2_df = f1_df[f1_df['team']==team]
		if len(f2_df) == 0:
			raise RuntimeError('Cannot find '+yname+' in NBA endpoint data')
		elif len(f2_df) == 1:
			return f2_df['id'].iloc[0]
		else:
			raise RuntimeError('Multiple player with last name '+lastname+' on team '
				+ team)


	def get_roster_ids(self, roster):
		roster_ids = {}
		for name, team in roster:
			roster_ids[name] = self.get_player_id(name,team)
		return roster_ids

	#Use pandas to add internal id and later on player_id from NBA
	#Use pandas in yahoofantasydata

class NBAData():

	CAT = {'FGM','FGA','FTM','FTA','PTS','FG3M','REB','AST','STL','BLK','TOV'}

	def __init__(self, roster):
		self.roster_info_getter = PlayersInfo()
		self.roster = self.roster_info_getter.get_roster_ids(roster)
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
