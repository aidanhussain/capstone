

def results_summary_to_dataframe(results):
    import pandas as pd
    
    '''take the result of an statsmodel results table and transforms it into a dataframe'''
    pvals = results.pvalues
    coeff = results.params
    conf_lower = results.conf_int()[0]
    conf_higher = results.conf_int()[1]

    results_df = pd.DataFrame({"pvals":pvals,
                               "coeff":coeff,
                               "conf_lower":conf_lower,
                               "conf_higher":conf_higher
                                })
    
    #Reordering...
    results_df = results_df[["coeff","pvals","conf_lower","conf_higher"]]
    results_df.reset_index(inplace = True) 
    results_df = results_df.rename(columns = {'index':'Regressor'})
    
    misc_df = {}
    misc_df['# of Observations'] = results.nobs
    misc_df['R-Squared'] = results.rsquared
    misc_df['Adjusted R-Squared'] = results.rsquared_adj



    
    results_df = results_df.append(misc_df, ignore_index = True)
    
    return results_df

def runRegression(x,y):
        
    import numpy as np
    import pandas as pd
    import statsmodels.api as sm
        
    # with statsmodels
    x = sm.add_constant(x) # adding a constant
     
    model = sm.OLS(y, x).fit()
    predictions = model.predict(x) 
     
    summary = model.summary()
    coefficients = model.params
    r_squared = model.rsquared
    adj_r_squared = model.rsquared_adj
    num_observations = model.nobs
    
    
    result_df = results_summary_to_dataframe(model)
    
    #print(summary)
    
    return summary, coefficients, r_squared, adj_r_squared, num_observations, result_df