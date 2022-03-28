from datetime import date, timedelta
from email.utils import encode_rfc2231
import boto3
import json
import socket
# Get Date of oldest snapshot taken from auto Snaps 
dt = date.today() - timedelta(6)

#Define how many days back you want ot keep auto snap shots. For example enter 10 would delete kept manual snaps older than 10 days 
retention = date.today() - timedelta(28)
# Define LightSail for Boto3
client = boto3.client('lightsail', region_name='us-west-2' )

# Get Todays date to compare to snapshot
today = date.today()
# print("Today's date:", today)
# print("Keeping snapshot from:", dt)

# aws lightsail copy-snapshot --region us-west-2 --source-resource-name Master-Tracker --restore-date 2022-03-19 --source-region us-west-2 --target-snapshot-name MasterTrackerSnap

# Display all available auto snapshots

# MAKE SURE THAT YOU HAVE SET THE HOST NAME TO REMAIN THE SAME AND THE HOST NAME MATCHES THE NAME OF THE INSTANCE
hostName = socket.gethostname()
availableSnaps = client.get_auto_snapshots(
    resourceName=hostName
)

# Convert dict to string so it doesn't look like shit when we're reading it. 
parsedSnaps = json.dumps(availableSnaps, indent=2, default=str)
print(parsedSnaps)


#Keep the oldest automatic snapshot 
dateString = str(dt)
snap = client.copy_snapshot(
    sourceResourceName=hostName,
    restoreDate=dateString,
    targetSnapshotName=dateString,
    sourceRegion='us-west-2'
 )


# Delete kept snapshot older than set date 
# Convert retention date to a string 
retStr = str(retention)
print(retStr)
removeOldestManualSnap = client.delete_instance_snapshot(
    instanceSnapshotName=retStr
)


