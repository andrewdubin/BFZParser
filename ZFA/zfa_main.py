import pandas as pd
import numpy as np
from values import dismissal

#Step 1: Import HMIS document into pandas dataframe, rename columns, drop un-needed ones and duplicates
file = input("File Name?: ")
df = pd.read_csv(file,parse_dates=['Program Start Date','Program End Date'])
df = df.rename(columns={"Program Start Date":"Date of Identification",'Case Number':'Client ID','Veteran Status (HUD)':'Veteran Status',"CH":"Chronic Status"})
df = df.drop(['Name','Gender (HUD)','Race and Ethnicity (HUD)','DOB'],axis=1)
df = df.drop_duplicates()
df = df.reset_index(drop=True)

#Step 2: Adding Household Type Column
#Maps programs for singles down to Single Adults, programs for families down to Family
household_type = {"HSC - Shelter":"Single Adults",
"Residential Program Center (RPC)":"Single Adults",
"Opportunity Place - Arlington":"Single Adults",
"DHS-Treatment on Wheels (TOW)":"Single Adults",
"Drop In":"Single Adults",
"Sullivan House":"Family",
"Family Home":"Family"}

df['Household Type'] = df['Program Name'].map(household_type)
#Downside to mapping by program names to household types due to contractual oddities (single females may want to be in family shelter)

#TAY steps since we don't have youth specific programs
for i in df[(df['Age'] >= 18) & (df['Age'] <= 24) & (df['Relationship'] == 'Self/Head of Household')].index:
    df.loc[i,'Household Type'] = 'Youth'

#Step 3: Adding Client ID Counter and Client ID Household Counter
#These aren't picked up by the aggregator, they're used to identify clients with multiple records so we can identify their Return to Active dates later
#Client ID Counter counts how many times a client appears in the dataset, as it contains 2 years of data so clients can reappear in our system throughout that timeframe.
df['Client ID Counter'] = df['Client ID'].map(df.groupby('Client ID').agg({'Client ID':'count'})['Client ID'])
#Client ID Household Counter. Same as Client ID counter but it is also pegged to household type.
#Example: A client may appear 3 times in the dataset, but they were a youth for two records then aged into a single adult.
#Client ID Household Counter would be 2 for the youth records, and 1 for the single adult record.
#This is the counter used for Return to Active calculations
#Initialize a dictionary with client IDs as keys and a dictionary of household type counts as values.
counter = {}
for i in df['Client ID']:
    if i not in counter:
        counter[i] = {"Single Adults":0,"Family":0,"Youth":0}
#Loop through dictionary
for j in counter:
    for k in df[df['Client ID']==j]['Household Type']:
        counter[j][k] += 1
df['Client ID Household Counter'] = np.nan
for i in df.index:
    df.loc[i,'Client ID Household Counter'] = counter[df.loc[i,'Client ID']][df.loc[i,'Household Type']]
df['Client ID Household Counter'] = df['Client ID Household Counter'].apply(int)

#Step 4: Remapping Chronic Column values
df['Chronic Status'] = df['Chronic Status'].map({'CH':"Yes",'Not CH':np.nan})

#Step 5, Remap all dismissal reasons from dismissals dictionary in values.py
df['Dismissal Reason'] = df['Dismissal Reason'].map(dismissal)

#Step 6, Populate Housing Move-In Date. Exit dates of any client record that exited to housing
df['Housing Move-In Date'] = df["Program End Date"][df["Dismissal Reason"]=="Housed"]

#Step 7, Populate Inactive Date. Exit dates of any client record that went inactive.
df['Inactive Date'] = df['Program End Date'][df["Dismissal Reason"]=="Inactive"]

#Step 8, Calculate 1stDateofID, then calculate Returned to Active Date (Date of Idenfication on newest record)
df['1stDateofID'] = df['Client ID'].map(df.groupby('Client ID').agg({'Date of Identification':'min'})['Date of Identification'])
df['Return to Active Date'] = np.nan
df.loc[(df['Client ID Household Counter']>1) & (df['1stDateofID']!=df['Date of Identification'])
,"Return to Active Date"] = df['Date of Identification']
df['Return to Active Date'] = pd.to_datetime(df['Return to Active Date'])

#Step 9, Find most recent move-in or inactive dates per client
df['Most Recent Move-In Date'] = df['Client ID'].map(df.groupby('Client ID').agg({'Housing Move-In Date':'max'})['Housing Move-In Date'])
df['Most Recent Inactive Date'] = df['Client ID'].map(df.groupby('Client ID').agg({'Inactive Date':'max'})['Inactive Date'])

#Step 10, Narrow down dataframe down to active clients and newly exited clients for the reporting month
#Code for inputting dates
dates = {}
dates["Reporting Year"] = input("Reporting Year? Enter four digits: ")
dates["Reporting Month"] = input("Reporting Month? Enter either proper string or number ")
dates['Start Date'] = pd.to_datetime(dates["Reporting Year"]+dates["Reporting Month"],format='%Y%m',errors='ignore')
dates['Last Day'] = dates['Start Date'].days_in_month
dates['Reporting Date'] = dates['Start Date'].replace(day=dates['Last Day'])

#Separate dataframe between active clients and exited clients, the recombine.
active_df = df[(df['Date of Identification']<=dates['Reporting Date']) &
((df['Program End Date'].isnull()==True) | (df['Program End Date']<df['Date of Identification']) | (df['Program End Date']>dates['Reporting Date']))]
exited_df = df[(df['Program End Date']>=dates['Start Date']) & (df['Program End Date']<=dates['Reporting Date'])]
filtered_df = pd.concat([active_df,exited_df])
filtered_df = filtered_df.sort_values('Date of Identification').drop_duplicates('Client ID',keep='first')
filtered_df = filtered_df.reset_index()
filtered_df = filtered_df.drop(['index'],axis=1)
filtered_df

#Step 11, Determine clients that "No longer meets population criteria" by demographic info
#All persons, all singles, veterans, chronic, chronic veteran, youth, families
print("\nHow many clients this month No longer meet population criteria?")
print("All clients ",exited_df['Dismissal Reason'].where(exited_df['Dismissal Reason']=="No longer meets population criteria").count())
print("Singles ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Household Type']=='Single Adults')).count())
print("Veterans ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Veteran Status']=='Yes')).count())
print("Chronic ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Chronic Status']=='Yes')).count())
print("Chronic Veterans ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Chronic Status']=='Yes')&(exited_df['Veteran Status']=='Yes')).count())
print("Youth ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Household Type']=='Youth')).count())
print("Family ",exited_df['Dismissal Reason'].where((exited_df['Dismissal Reason']=="No longer meets population criteria")&(exited_df['Household Type']=='Family')).count())

#Step 12, Calculate BFZ Reporting Metrics to make sure numbers match
#This is just for my end as an internal check, not identical to how BFZ aggregator calculates it.
print("\nBFZ Reporting Metrics")
print("Actively Homeless ", len(active_df),
"+",exited_df['Client ID'].where(exited_df['Dismissal Reason']=='No longer meets population criteria').count(),'No longer meet population criteria')
print("Housing Placements ", exited_df['Client ID'].where(exited_df['Dismissal Reason']=='Housed').count())
print("Moved to Inactive ", exited_df['Client ID'].where(exited_df['Dismissal Reason']=='Inactive').count())
print("Newly Identified Inflow ",len(active_df.loc[(dates['Start Date']<=active_df['Date of Identification']) & (active_df['Date of Identification']<=dates['Reporting Date'])]))
def housing_lot():
    housed = exited_df[exited_df['Dismissal Reason']=='Housed']
    lot = [(housed.loc[i,'Program End Date'] - housed.loc[i,'Date of Identification']) for i in housed.index]
    average = 0
    for i in lot:
        average += i.days
    return average/len(lot)
print("Average Length of Time from ID to Housing Placement ",housing_lot())
def rtad_counter():
    rtad = active_df[active_df['Return to Active Date'].isnull()==False]
    counter = 0
    for i in rtad.index:
        if (rtad.loc[i,"Return to Active Date"].year==dates['Reporting Date'].year)& (rtad.loc[i,"Return to Active Date"].month==dates['Reporting Date'].month):
            counter += 1
    return counter
print("Returned to Active ",rtad_counter())

#Step 13, Output
output = input("Parsing Finished. Output File Name?: ")
if output=="N":
    print("No Output")
else:
    filtered_df.to_csv(output)