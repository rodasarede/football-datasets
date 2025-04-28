import pandas as pd
import numpy as np
from scipy.stats import poisson

# Load your dataset
# Replace 'your_dataset.csv' with the actual dataset file
data = pd.read_csv('datasets/liga-portugal/season-2425.csv')

# Example dataset columns: ['HomeTeam', 'AwayTeam', 'HomeGoals', 'AwayGoals']


# Calculate league averages
league_avg_home_goals = data['FTHG'].mean()  # Full Time Home Goals
league_avg_away_goals = data['FTAG'].mean()  # Full Time Away Goals

team_stats = {}
teams = set(data['HomeTeam']).union(set(data['AwayTeam']))


for team in teams:
    home_games = data[data['HomeTeam'] == team]
    away_games = data[data['AwayTeam'] == team]
    
    team_stats[team] = {
        'attack_home': home_games['FTHG'].mean(),  # Avg goals scored at home
        'attack_away': away_games['FTAG'].mean(),  # Avg goals scored away
        'defense_home': home_games['FTAG'].mean(), # Avg goals conceded at home
        'defense_away': away_games['FTHG'].mean()  # Avg goals conceded away
    }
    

# Poisson prediction function
def predict_match(home_team, away_team, max_goals=5):
    # Get team stats with fallback to league average if missing
    home_attack = team_stats.get(home_team, {}).get('attack_home', league_avg_home_goals)
    away_defense = team_stats.get(away_team, {}).get('defense_away', league_avg_home_goals)
    away_attack = team_stats.get(away_team, {}).get('attack_away', league_avg_away_goals)
    home_defense = team_stats.get(home_team, {}).get('defense_home', league_avg_away_goals)
    
    # Calculate expected goals
    home_exp = (home_attack * away_defense) / league_avg_home_goals
    away_exp = (away_attack * home_defense) / league_avg_away_goals
    
    # Calculate probabilities for each possible scoreline
    home_probs = [poisson.pmf(i, home_exp) for i in range(max_goals+1)]
    away_probs = [poisson.pmf(i, away_exp) for i in range(max_goals+1)]
    
    # Calculate match outcome probabilities
    home_win = sum(home*p_away for i, home in enumerate(home_probs) 
                          for j, p_away in enumerate(away_probs) if i > j)
    draw = sum(home*p_away for i, home in enumerate(home_probs) 
                      for j, p_away in enumerate(away_probs) if i == j)
    away_win = 1 - home_win - draw
    
    return {
        'expected_goals': (home_exp, away_exp),
        'score_probs': np.outer(home_probs, away_probs),
        'outcome_probs': {'home': home_win, 'draw': draw, 'away': away_win},
        'top_scorelines': sorted([(f"{i}-{j}", home_probs[i]*away_probs[j]) 
                                 for i in range(max_goals+1) 
                                 for j in range(max_goals+1)], 
                                key=lambda x: -x[1])[:5]
    }


# Example usage
home_team = 'Sporting'
away_team = 'Porto'

prediction = predict_match(home_team, away_team)
if prediction:
    print(f"\nPrediction for {home_team} vs {away_team}:")
    print(f"Expected goals: {prediction['expected_goals'][0]:.2f}-{prediction['expected_goals'][1]:.2f}")
    print("\nOutcome probabilities:")
    print(f"  {home_team} win: {prediction['outcome_probs']['home']*100:.1f}%")
    print(f"  Draw: {prediction['outcome_probs']['draw']*100:.1f}%")
    print(f"  {away_team} win: {prediction['outcome_probs']['away']*100:.1f}%")
    print("\nMost likely scorelines:")
    for score, prob in prediction['top_scorelines']:
        print(f"  {score}: {prob*100:.1f}%")
