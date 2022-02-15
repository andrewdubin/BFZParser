import pandas as pd
import numpy as np

#Step 1: Import document, Change Program Start Date to Date of Identification
file = input("File Name?: ")
df = pd.read_csv(file,parse_dates=['Program Start Date','Program End Date'])
df = df.rename(columns={"Program Start Date":"Date of Identification",'Case Number':'Client ID','Veteran Status (HUD)':'Veteran Status'})
df = df.drop(["Relationship","Family Name",'Name'],axis=1)
df = df.drop_duplicates()
df = df.reset_index()
df = df.drop(['index'],axis=1)

#Step 2: Adding Household Type Column
household_type = {"Arlington Zero: Chronic - Veterans Only":"Single Adults",
"Arlington Zero: Single Adults":"Single Adults",
"Arlington Zero: Families":"Families",
"Arlington Zero: TAY":"Youth"}
df['Household Type'] = df['Program Name'].map(household_type)

#Step 3: Adding Client ID Counter and Client ID Household Counter
#Client ID Counter
df['Client ID Counter'] = df['Client ID'].map(df.groupby('Client ID').agg({'Client ID':'count'})['Client ID'])
#Client ID Household Counter
counter = {}
for i in df['Client ID']:
    if i not in counter:
        counter[i] = {"Single Adults":0,"Families":0,"Youth":0}
for j in counter:
    for k in df[df['Client ID']==j]['Household Type']:
        counter[j][k] += 1
df['Client ID Household Counter'] = np.nan
for i in df.index:
    df.loc[i,'Client ID Household Counter'] = counter[df.loc[i,'Client ID']][df.loc[i,'Household Type']]

#Step 4: Adding Chronic Column
#If client is in Chronic & Vet and 'No' to Veteran Status, then they are chronic
df['Chronic Status'] = np.nan
df.loc[(df['Program Name']=="Arlington Zero: Chronic - Veterans Only") & (df['Veteran Status']!="Yes")
,"Chronic Status"] = "Yes"

#Step 5, Remap all dismissal reasons
from values import dismissal
df['Dismissal Reason'] = df['Dismissal Reason'].map(dismissal)

#Step 6, Populate Housing Move-In Date
df['Housing Move-In Date'] = df["Program End Date"][df["Dismissal Reason"]=="Housed"]

#Step 7, Populate Inactive Date
#Do we consider those with program end date and null dismissal reasons as inactive?
df['Inactive Date'] = df['Program End Date'][df["Dismissal Reason"]=="Inactive"]

#Step 8, Calculate 1stDateofID, then calculate Returned to Active Date (Date of Idenfication on second record)
#Consider revising Return to Active Date formula
df['1stDateofID'] = df['Client ID'].map(df.groupby('Client ID').agg({'Date of Identification':'min'})['Date of Identification'])
df['Return to Active Date'] = np.nan
df.loc[(df['Client ID Household Counter']>1) & (df['1stDateofID']!=df['Date of Identification'])
,"Return to Active Date"] = df['Date of Identification']
df['Return to Active Date'] = pd.to_datetime(df['Return to Active Date'])

#Step 9, Calculate most recent move-in or inactive dates
df['Most Recent Move-In Date'] = df['Client ID'].map(df.groupby('Client ID').agg({'Housing Move-In Date':'max'})['Housing Move-In Date'])
df['Most Recent Inactive Date'] = df['Client ID'].map(df.groupby('Client ID').agg({'Inactive Date':'max'})['Inactive Date'])

#Step 10, Narrow down dataframe down to active clients and newly exited clients for the reporting month
reporting_year = input("Reporting Year? Enter four digits: ")
reporting_month = input("Reporting Month? Enter month number: ")
reporting_date = pd.to_datetime(reporting_year+reporting_month,format='%Y%m',errors='ignore')
num_of_days = reporting_date.days_in_month
dates = {}
dates['Reporting Date'] = str(reporting_date.year)+'-'+ str(reporting_date.month) +'-'+ str(num_of_days)
dates['Start Date'] = str(reporting_date.year)+'-'+ str(reporting_date.month) +'-1'

active_df = df[(df['Date of Identification']<=dates['Reporting Date']) &
((df['Program End Date'].isnull()==True) | (df['Program End Date']<df['Date of Identification']) | (df['Program End Date']>dates['Reporting Date']))]
exited_df = df[(df['Program End Date']>=dates['Start Date']) & (df['Program End Date']<=dates['Reporting Date'])]
filtered_df = pd.concat([active_df,exited_df])
filtered_df = filtered_df.reset_index()
filtered_df = filtered_df.drop(['index'],axis=1)

#Step 11, Output
output = input("Parsing Finished. Output File Name?: ")
filtered_df.to_csv(output)

#Step 12, Determine clients that "No longer meets population criteria" by demographic info
#All persons, all singles, veterans, chronic, chronic veteran, youth, families
print("\nHow many clients this month No longer meet population criteria?")
print("All clients ",filtered_df['Dismissal Reason'].where(filtered_df['Dismissal Reason']=="No longer meets population criteria").count())
print("Singles ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Household Type']=='Single Adults')).count())
print("Veterans ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Veteran Status']=='Yes')).count())
print("Chronic ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Chronic Status']=='Yes')).count())
print("Chronic Veterans ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Chronic Status']=='Yes')&(filtered_df['Veteran Status']=='Yes')).count())
print("Youth ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Household Type']=='Youth')).count())
print("Families ",filtered_df['Dismissal Reason'].where((filtered_df['Dismissal Reason']=="No longer meets population criteria")&(filtered_df['Household Type']=='Families')).count())

#Step 13, Calculate BFZ Reporting Metrics to make sure numbers match
print("\nBFZ Reporting Metrics")
print("Actively Homeless ", filtered_df['Client ID'].where(filtered_df['Program End Date'].isnull()==True).nunique())
print("Housing Placements ", filtered_df['Client ID'].where(filtered_df['Dismissal Reason']=='Housed').nunique())
print("Moved to Inactive ", filtered_df['Client ID'].where(filtered_df['Dismissal Reason']=='Inactive').nunique())
def newly_identified_number():
    nin = {}
    for i in filtered_df['Client ID']:
        if i not in nin:
            nin[i] = False
    for j in nin:
        for k in filtered_df[filtered_df['Client ID']==j]['Date of Identification']:
            if k.year == reporting_date.year and k.month == reporting_date.month:
                nin[j] = True
    nin_counter = 0
    for x in nin:
        if x == True:
            nin_counter += 1
    return nin_counter
print("Newly Identified Inflow ",newly_identified_number())

def housing_lot():
    housed = filtered_df[filtered_df['Dismissal Reason']=='Housed']
    lot = [(housed.loc[i,'Program End Date'] - housed.loc[i,'Date of Identification']) for i in housed.index]
    average = 0
    for i in lot:
        average += i.days
    return average/len(lot)
print("Average Length of Time from ID to Housing Placement ",housing_lot())