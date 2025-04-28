
import pandas as pd
import os

def get_season_years(filename):
    """Extracts a readable season like 2000-2001 from filename like 'season-0001.csv'"""
    base = filename.replace('season-', '').replace('.csv', '')
    if len(base) == 4:
        start = int("20" + base[:2])
        end = int("20" + base[2:])
    else:
        return None
    return (start, end)

def update_team_stats(table, team, gf, ga, ht_gc , second_half_gc ,result, odds):
    """Updates the classification stats for a single team."""
    if team not in table:
        table[team] = {'MP': 0, 'W': 0, 'D': 0, 'L': 0, 'GF': 0, 'GA': 0, 'Pts': 0,  'HTGA_3plus': 0, 'HTGA_2plus' : 0,  '2NDHALF_3PLUS' : 0, 'HTGC': 0, 'FAVOURITE_2_1stHalf': 0, 'GamesAsFavourites': 0, '%' : 0}

    table[team]['MP'] += 1
    table[team]['GF'] += gf
    table[team]['GA'] += ga
    table[team]['HTGC'] += ht_gc
    if result == 'W':
        table[team]['W'] += 1
        table[team]['Pts'] += 3
        lucro = odds * 100 - 100
        if odds >= 1.2:
            table[team]['%'] += lucro
    elif result == 'D':
        table[team]['D'] += 1
        table[team]['Pts'] += 1
        table[team]['%'] -= 100
    else:
        table[team]['L'] += 1
        table[team]['%'] -= 100
    if ht_gc >= 2:
        table[team]['HTGA_2plus'] += 1
    if ht_gc >= 3:
        table[team]['HTGA_3plus'] += 1
    if second_half_gc >= 3:
        table[team]['2NDHALF_3PLUS'] += 1 
    if calculate_percentage_win_odds(odds) >= 0.5 and ht_gc >= 2:
        table[team]['FAVOURITE_2_1stHalf'] += 1
    if calculate_percentage_win_odds(odds) >= 0.5:
        table[team]['GamesAsFavourites'] += 1
    if isOver2_5(gf, ga):
        #+=1
        pass
    else:
        pass

def calculate_percentage_win_odds(odds):
    return 1 / odds if odds > 0 else 0
 
def isOver2_5(fthg, ftag):
    if fthg + ftag > 2.5 :
        return True
    return False

def get_classification(league_dir, start_year=None, end_year=None, top_n=10):
    """
    Builds a league classification for a given league folder.
    league_dir: path to the folder like 'datasets/premier-league'
    start_year, end_year: filter seasons by start year (e.g. 2003) and end year (e.g. 2023)
    top_n: number of top teams to show
    """
    table = {}
    files = sorted([f for f in os.listdir(league_dir) if f.endswith('.csv')])

    for file in files:
        season_years = get_season_years(file)
        if not season_years:
            continue

        season_start, _ = season_years
        if (start_year and season_start < start_year) or (end_year and season_start > end_year):
            continue

        df = pd.read_csv(os.path.join(league_dir, file))
        if 'FTHG' not in df or 'FTAG' not in df or 'FTR' not in df:
            continue  # skip invalid files

        for _, row in df.iterrows():
            try:
                home, away = row['HomeTeam'], row['AwayTeam']
                fthg, ftag, result = row['FTHG'], row['FTAG'], row['FTR']
                hthg, htag = row['HTHG'], row['HTAG']
                hOdd, dOdd, aOdd = row['B365H'], row['B365D'], row['B365A']
                #plus2_5, under2_5 = row[''], row['']
                h2nd_half_gc = ftag - htag
                a2nd_half_gc =  fthg - hthg
            except KeyError:
                continue

            if result == 'H':
                update_team_stats(table, home, fthg, ftag, htag, h2nd_half_gc, 'W', hOdd)
                update_team_stats(table, away, ftag, fthg, hthg, a2nd_half_gc, 'L', aOdd)
            elif result == 'A':
                update_team_stats(table, home, fthg, ftag, htag, h2nd_half_gc, 'L', hOdd)
                update_team_stats(table, away, ftag, fthg, hthg, a2nd_half_gc, 'W', aOdd)
            elif result == 'D':
                update_team_stats(table, home, fthg, ftag, htag ,h2nd_half_gc, 'D', hOdd)
                update_team_stats(table, away, ftag, fthg, hthg, a2nd_half_gc, 'D', aOdd)

    # Convert to DataFrame
    df_table = pd.DataFrame.from_dict(table, orient='index')
    df_table['GD'] = df_table['GF'] - df_table['GA']
    df_table = df_table.sort_values(by=['HTGA_3plus','Pts', 'GD', 'GF'], ascending=[True, False, False, False])

    # Print Top N
    #print(f"\n📊 League Classification ({start_year or 'All Seasons'} - {end_year or 'Present'})")
    #print(df_table[['MP', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts', 'HTGA_3plus']].head(top_n))

    return df_table

def get_global_ranking(datasets_dir='datasets', start_year=None, end_year=None, top_n=50):
    """
    Creates a global ranking of the best teams across all leagues.
    """
    league_dirs = [d for d in os.listdir(datasets_dir) 
                  if os.path.isdir(os.path.join(datasets_dir, d))]
    
    all_teams = []
    
    for league_dir in league_dirs:
        full_path = os.path.join(datasets_dir, league_dir)
        league_name = league_dir.replace('-', ' ').title()
        
        try:
            df = get_classification(full_path, start_year, end_year, top_n=None)
            # The team names are in the index - reset it to make it a column
            df = df.reset_index().rename(columns={'index': 'Team'})
            df['League'] = league_name
            all_teams.append(df)
        except Exception as e:
            print(f"⚠️ Error processing {league_name}: {str(e)}")
            continue
    
    if not all_teams:
        print("❌ No league data found.")
        return None
    
    # Combine all leagues
    global_df = pd.concat(all_teams)
    
    # Calculate Points Per Match
    global_df['Pts_Per_Match'] = global_df['Pts'] / global_df['MP']
    global_df['HGC_Per_Match'] = global_df['HTGC'] / global_df['MP']
    # Sort by performance metrics

    global_df = global_df.sort_values(
        by=['%','FAVOURITE_2_1stHalf','HTGA_3plus', 'HGC_Per_Match', 'Pts_Per_Match'], 
        ascending=[False,True, True, True, False]
    )
    
    # Reset index for ranking
    global_df.reset_index(drop=True, inplace=True)
    global_df.index += 1
    
    # Print results
    print(f"\n{'=' * 80}")
    print(f"🌍 GLOBAL FOOTBALL RANKING ({start_year or 'All Seasons'} - {end_year or 'Present'})")
    print(f"Top {top_n} Teams Across All Leagues")
    print(f"{'=' * 80}\n")
    

    # Select columns that actually exist in the DataFrame
    available_columns = [col for col in ['League', 'Team', 'MP', 'W', 'D', 'L', 'GF', 'GA', 'GD', 'Pts', 'HTGA_3plus','2NDHALF_3PLUS' ,'Pts_Per_Match', 'HGC_Per_Match', 'FAVOURITE_2_1stHalf', 'GamesAsFavourites', '%'] 
                        if col in global_df.columns]
    
    with pd.option_context('display.max_rows', None, 'display.max_columns', None, 'display.width', 1000):
        print(global_df[available_columns].head(top_n))
    
    return global_df
# === Example Calls ===

# ⚽ All-time Premier League
#get_classification('datasets/premier-league', top_n=20)

# 📅 Last 20 years only
#get_classification('datasets/premier-league', start_year=2024, end_year=2024, top_n=8)

get_global_ranking(start_year=2020  , end_year=2024, top_n=100)