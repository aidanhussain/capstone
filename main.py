import numpy as np
import pandas as pd
import statsmodels.api as sm
import funclib as fl
#tetst

#Where we set the parameters of the regression and the forecast
rawData = pd.read_csv('stats.csv')
ageDeltaFile = pd.read_csv('ageDelta.csv')
appliedCoefficientRange = (2015, 2021) #Seasons included in calculating coefficient for the backtest; (start_year, end_year)
regressionMinPAs = 200
regressors = ['hard_hit_percent','sweet_spot_percent','groundballs_percent','launch_angle_avg','oz_contact_percent','sprint_speed','b_k_percent','poorlyweak_percent','linedrives_percent','pull_percent','flareburner_percent','poorlytopped_percent','whiff_percent','z_swing_miss_percent','oz_swing_miss_percent','poorlyunder_percent','popups_percent']
regressand = 'on_base_plus_slg'
reversionWeight = 0.3 #How much weight to put on reversion to prior year performance

lookbackSeasons = 2 #If player has less than this number of seasons, program will only use those seasons
minSampleSize = 300 #Minimum number of PAs needed in lookback period to forecast
minForwardSampleSize = 250 #Minimum number of PAs needed in forecast period to assess forecast accuracy
forecastNextYear  = True

#Create player lookup
playerLookup = rawData.copy()
playerLookup = playerLookup[['player_id',' first_name','last_name']]
playerLookup['Name'] = playerLookup[' first_name'] + " " + playerLookup['last_name']


#Limit dataframe to columns we need, drop rows that have missing data
rawDataRegression = rawData.copy()

cols = regressors.copy()
cols.append(regressand)
cols.append('b_total_pa')
cols.append('year')
cols.append('player_id')

rawDataRegression = rawDataRegression[cols]
rawDataRegression = rawDataRegression[rawDataRegression['b_total_pa'] >= regressionMinPAs]
rawDataRegression = rawDataRegression.dropna()



#Run regression on all data, then each year of data
years = []
for i in range(appliedCoefficientRange[0],appliedCoefficientRange[1]):
    years.append(i)
years.insert(0,-1)

writer = pd.ExcelWriter("output.xlsx", engine = 'xlsxwriter')

regressionResultDict = {}

for year in years:
    if (year == -1):
        rawDataRegression = rawDataRegression[(rawDataRegression['year'] >= appliedCoefficientRange[0]) & (rawDataRegression['year'] <= appliedCoefficientRange[1])]
        x = rawDataRegression[regressors]
        y = rawDataRegression[[regressand]]
        
        summary, coefficients, r_squared, adj_r_squared, num_observations, result_df = fl.runRegression(x,y)
        
        regressionResultDict[-1] = [summary, coefficients, r_squared, adj_r_squared, num_observations,  result_df]
        
        result_df.to_excel(writer, sheet_name = str("All Data Regression Results"))         
 
        
    else:
        print(year)
        univ = rawDataRegression[rawDataRegression['year'] == year]
        x = univ[regressors]
        y = univ[[regressand]]

        summary, coefficients, r_squared, adj_r_squared, num_observations,result_df = fl.runRegression(x,y)
        

        
        regressionResultDict[year] = [summary, coefficients, r_squared, adj_r_squared, num_observations, result_df]
        
        result_df.to_excel(writer, sheet_name = str(year) + " Regression Results") 



#Prepare a DataFrame which tracks which years will be included in the backtest
forecastYears = years.copy()
forecastYears = forecastYears[lookbackSeasons+1:]
if forecastNextYear:
    forecastYears.append(forecastYears[-1]+1)


#Creates a DataFrame which tracks the accuracy of each period's backtest forecast
resultsCols = ['Year','num_observations','Improvement Relative Error','Improvement Absolute Error','Actual Relative Error','Actual Absolute Error','Actual Absolute Error Squared']
runningResults = pd.DataFrame(columns = resultsCols) #Track aggregate accuracy for each period of backtest


#Year = year we are forecasting for...
for year in forecastYears:
    univ = rawData.copy()
    univ = univ[cols]
    univ = univ.drop(columns = [regressand])
    univ = univ[(univ['year'] >= year - lookbackSeasons) & (univ['year'] <= year - 1)]
    univ = univ.drop(columns=['year'])


    #Calculate total number of PAs in lookback period for each player
    totalPAsDF = univ.copy()
    totalPAsDF = totalPAsDF[['player_id','b_total_pa']]
    totalPAsDF = totalPAsDF.rename({'b_total_pa': 'periodPAs'}, axis=1)
    totalPAsDF = totalPAsDF.groupby('player_id').sum()
    #Join with univ DF, calculate relative weight of each year in lookback period, then calculate weighted average for each statistic
    univ = univ.join(totalPAsDF, on='player_id')
    univ = univ[(univ['periodPAs'] >=minSampleSize)] #Get rid of players without enough PAs             
    univ['periodPAs'] = univ['b_total_pa'] / univ['periodPAs']
    for col in regressors:
        univ[col] = univ[col] * univ['periodPAs']
    univ = univ.drop(columns=['periodPAs'])
    univ = univ.drop(columns=['b_total_pa'])
    univ = univ.groupby('player_id').sum()
    
    
    #Forecast regressand 
    for col in regressors:
        univ[col] = univ[col] * coefficients[col]
    univ = univ.sum(axis=1) + coefficients['const']
    
    univ = univ.to_frame()
    
    #Link Univ DF with Ages for each player
    agelookup = rawData.copy()
    agelookup = agelookup[rawData['year'] == year] 
    agelookup = agelookup[['player_id','player_age']] 
    
    #Link Univ DF with last season's OPS for each player to allow for reversion weighting
    opsLookup = rawData.copy()
    opsLookup = opsLookup[rawData['year'] == year - 1] 
    opsLookup = opsLookup[['player_id','b_total_pa','on_base_plus_slg']] 
    opsLookup = opsLookup[(opsLookup['b_total_pa'] >=minSampleSize / 2)] #Get rid of players without enough PAs to weight (1/2 of required sample size)     
    opsLookup = opsLookup.rename({'on_base_plus_slg': 'Last Season OPS'},axis=1)  # new method

    
    univ = univ.merge(agelookup,on='player_id')
    
    #Pull in age delta adjustment values
    ageDeltaFile = ageDeltaFile[['Age','Adjustment']]
    univ = univ.merge(ageDeltaFile, left_on='player_age', right_on='Age')
    univ.columns.values[1] = (regressand + "_forecast")
    univ[(regressand + "_forecast")] = univ[(regressand + "_forecast")] + univ['Adjustment']
    univ = univ.drop(columns = ['player_age','Age','Adjustment'])
    
    #Calculate reversion weighted forecast in age delta adjustment values
    univ = univ.merge(opsLookup,on='player_id')
    univ['on_base_plus_slg_forecast'] = univ['on_base_plus_slg_forecast'] * (1-reversionWeight) + univ['Last Season OPS']
    univ = univ.drop(columns = ['Last Season OPS'])

    
    
    
    forecastDF = univ.copy()
    forecastDF.columns.values[1] = (regressand + "_forecast")

    #Create DF of only the "actual" performance for the year we have forecasted
    if (year != 2023): #change to not be hardcoded later...
        actualPerf = rawData.copy()
        actualPerf = actualPerf[cols]
        actualPerf = actualPerf[(actualPerf['year'] == year)]
        actualPerf = actualPerf[(actualPerf['b_total_pa'] > minForwardSampleSize)] #Eliminate seaosons with too few at bats to assess accuracy
        actualPerf = actualPerf[['player_id',regressand]]
        
        #Join actual performance with forecast so we can calculate forecast versus actual accuracy
        forecastDF = forecastDF.merge(actualPerf, on='player_id', how='left')
        forecastDF = forecastDF.dropna()
        
        #Isolate prior year's statsitcis and merge with forecasted statistics so we can calculate improvement related accuracy
        prevYear = rawData.copy()
        prevYear = prevYear[['player_id','year',regressand,'b_total_pa']]
        prevYear.columns.values[2] = ('Prior Year ' + regressand)
        prevYear.columns.values[3] = ('Prior Year PA')
        prevYear = prevYear[(prevYear['year'] == year - 1)]
        prevYear = prevYear.drop(columns = ['year'])
        forecastDF = forecastDF.merge(prevYear,on='player_id', how = 'left')
        forecastDF = forecastDF[(forecastDF['Prior Year PA'] >= minForwardSampleSize)] 
        forecastDF['Improvement_forecast'] = forecastDF[regressand + "_forecast"] - forecastDF['Prior Year ' + regressand]
        forecastDF['Improvement_actual'] = forecastDF[regressand] - forecastDF['Prior Year ' + regressand]
        
        #Create / calculate accuracy metrics
        forecastDF['num_observations'] = len(forecastDF.index)
        forecastDF['Actual Relative Error'] = forecastDF[regressand] - forecastDF[regressand + "_forecast"]
        forecastDF['Actual Absolute Error'] = abs(forecastDF[regressand] - forecastDF[regressand + "_forecast"])
        forecastDF['Actual Absolute Error Squared'] = (forecastDF[regressand] - forecastDF[regressand + "_forecast"]) ** 2
        forecastDF['Improvement Relative Error'] = forecastDF['Improvement_actual'] - forecastDF["Improvement_forecast"]
        forecastDF['Improvement Absolute Error'] = abs(forecastDF['Improvement_actual'] - forecastDF["Improvement_forecast"])
        
        
        #Output this forecast data, linked with player's actual name, to Excel
        forecastOutput = forecastDF.copy()
        forecastOutput = playerLookup.merge(forecastDF, on='player_id', how='left')
        forecastOutput = forecastOutput.dropna()
        forecastOutput.to_excel(writer, sheet_name = str(year) + " Forecast Results") 
        
        
        #Average the metrics, add to running metric tracker
        preserved_ForecastDF = forecastDF.copy()
        forecastDF = forecastDF.set_index('player_id')
        forecastDF = forecastDF.mean(axis=0) 
        forecastDF['Year'] = year
        forecastDF = forecastDF.to_frame()
        forecastDF = forecastDF.transpose()
        
        forecastDF = forecastDF[resultsCols]
        runningResults = runningResults.append(forecastDF)       
    else:           
        forecastOutput = forecastDF.copy()
        forecastOutput = playerLookup.merge(forecastDF, on='player_id', how='left')
        forecastOutput = forecastOutput.dropna()
        forecastOutput.to_excel(writer, sheet_name = str(year) + " Forecast Results") 
runningResults.loc['Average'] = runningResults.mean()
runningResults.loc['Average']['Year'] = np.NaN
runningResults.to_excel(writer, sheet_name = 'Aggregate Backtest Results') 
    

#Create summary sheet on Excel output
row = 0
df_list = [result_df, runningResults]
for dataframe in df_list:
    dataframe.to_excel(writer,sheet_name="Summary",startrow=row , startcol=0)   
    row = row + len(dataframe.index) + 3 + 1


writer.save()
writer.close()
        
        


