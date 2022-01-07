import pandas as pd
import numpy as np

#Step 1: Import document, Change Program Start Date to Date of Identification
file = input("File Name?: ")
df = pd.read_csv(file)
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
df.loc[(df['Program Name']=="Arlington Zero: Chronic - Veterans Only") & (df['Veteran Status']=="No")
,"Chronic Status"] = "Yes"

#Step 5, Remap all dismissal reasons
from values import dismissal
df['Dismissal Reason'] = df['Dismissal Reason'].map(dismissal)

#Step 6, Populate Housing Move-In Date
df['Housing Move-In Date'] = df["Program End Date"][df["Dismissal Reason"]=="Housed"]
df['Housing Move-In Date']

#Step 7, Populate Inactive Date
#Do we consider those with program end date and null dismissal reasons as inactive?
df['Inactive Date'] = df['Program End Date'][df["Dismissal Reason"]!="Housed"]

#Step 8, Calculate 1stDateofID, then calculate Returned to Active Date (Date of Idenfication on second record)
#Consider revising Return to Active Date formula
df['1stDateofID'] = df['Client ID'].map(df.groupby('Client ID').agg({'Date of Identification':'min'})['Date of Identification'])
df['Return to Active Date'] = np.nan
df.loc[(df['Client ID Counter']>1) & (df['1stDateofID']!=df['Date of Identification'])
,"Return to Active Date"] = df['Date of Identification']

#Step 9, Output
output = input("Parsing Finished. Output File Name?: ")
df.to_csv(output)

#Step 10, Determine clients that "No longer meets population criteria" by demographic info
#All persons, all singles, veterans, chronic, chronic veteran, youth, families
print("How many clients this month No longer meet population criteria?")
print("All clients ",df['Dismissal Reason'].where(df['Dismissal Reason']=="No longer meets population criteria").count())
print("Singles ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Household Type']=='Single Adults')).count())
print("Veterans ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Veteran Status']=='Yes')).count())
print("Chronic ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Chronic Status']=='Yes')).count())
print("Chronic Veterans ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Chronic Status']=='Yes')&(df['Veteran Status']=='Yes')).count())
print("Youth ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Household Type']=='Youth')).count())
print("Families ",df['Dismissal Reason'].where((df['Dismissal Reason']=="No longer meets population criteria")&(df['Household Type']=='Families')).count())