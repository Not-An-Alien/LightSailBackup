#!/usr/bin/python
from datetime import date, timedelta, datetime
from email.utils import encode_rfc2231
import boto3
import json
import socket
import subprocess
import os
import time
import re
import pipes
import zipfile
import shutil
from dotenv import load_dotenv

load_dotenv()
# Setup credentials 
ENV = '/.env'
try:
    os.stat(ENV)
    print("Env exists moving on")
except:
    open(ENV, 'a').close()
    print("This appears to be your first time running this. Please populate the .env file with the following")
    db_user = input("Who is the database user?: ")
    db_pass = input("Please enter the db password: ")
    db_ = input("Please enter the db name you want to backup: ")
    AWS_ACCESS_KEY_ID = input("Please enter your ACCESS ID: ")
    AWS_SECRET_ACCESS_KEY = input("Please enter your ACCESS KEY: ")
    BUCKET_NAME = input("Please enter your s3 bucket name: ")
    Retention = input("Please enter how many days of backups you would like to keep, EX: 28 would keep 28 days worth of backups from todays date")
    print("cool, everythings configured please run the script again")
    

    # Create and populate .env 
    file1 = open(".env", "w")
    L = ["AWS_ACCESS_KEY_ID="+AWS_ACCESS_KEY_ID+" \n",
         "AWS_SECRET_ACCESS_KEY="+AWS_SECRET_ACCESS_KEY+" \n",
         "db_user="+db_user+"\n",
         "db_pass="+db_pass+"\n",
         "db_="+db_+"\n",
         "bucket_name="+BUCKET_NAME+"\n"]
    file1.writelines(L)
    file1.close()
    exit()



# Define LightSail for Boto3
client = boto3.client('lightsail', region_name='us-west-2' )

# Get Todays date to compare to snapshot
today = str(date.today())

# MAKE SURE THAT YOU HAVE SET THE HOST NAME TO REMAIN THE SAME AND THE HOST NAME MATCHES THE NAME OF THE INSTANCE
hostName = socket.gethostname()
# availableSnaps = client.get_auto_snapshots(
#     resourceName=hostName
# )
 
# MySQL database details to which backup to be done. Make sure below user having enough privileges to take databases backup.
# To take multiple databases backup, create any file like /backup/dbnames.txt and put databases names one on each line and assigned to DB_NAME variable.
 
DB_HOST = 'localhost' 
DB_USER =str(os.getenv('db_user'))
DB_USER_PASSWORD = str(os.getenv('db_pass'))
#DB_NAME = '/backup/dbnameslist.txt'
DB_NAME =str(os.getenv('db_'))
bucket_name = str(os.getenv('bucket_name'))
retention_days = int(os.getenv('Retention'))
BACKUP_PATH = '/backup'
s3StagingPath = '/s3Stage'
# Getting current DateTime to create the separate backup folder like "20180817-123433".
DATETIME = time.strftime('%Y%m%d-%H%M%S')
TODAYBACKUPPATH = BACKUP_PATH + '/' + DATETIME

# Checking if backup folder already exists or not. If not exists will create it.
try:
    os.stat(BACKUP_PATH)
except:
    os.mkdir(BACKUP_PATH)

try: 
    os.stat(s3StagingPath)
except:
    os.mkdir(s3StagingPath)
 
# Code for checking if you want to take single database backup or assinged multiple backups in DB_NAME.
print ("checking for databases names file.")
if os.path.exists(DB_NAME):
    file1 = open(DB_NAME)
    multi = 1
    print ("Databases file found...")
    print ("Starting backup of all dbs listed in file " + DB_NAME)
else:
    print ("Databases file not found...")
    print ("Starting backup of database " + DB_NAME)
    multi = 0
 
# Starting actual database backup process.
if multi:
   in_file = open(DB_NAME,"r")
   flength = len(in_file.readlines())
   in_file.close()
   p = 1
   dbfile = open(DB_NAME,"r")
 
   while p <= flength:
       db = dbfile.readline()   # reading database name from file
       db = db[:-1]         # deletes extra line
       dumpcmd = "mysqldump -h " + DB_HOST + " -u " + DB_USER + " -p" + DB_USER_PASSWORD + " " + db + " > " + pipes.quote(BACKUP_PATH) + "/" + db + ".sql"
       os.system(dumpcmd)
       gzipcmd = "gzip " + pipes.quote(BACKUP_PATH) + "/" + db + ".sql"
       os.system(gzipcmd)
       p = p + 1
   dbfile.close()
else:
   db = DB_NAME
   dumpcmd = "mysqldump -h " + DB_HOST + " -u " + DB_USER + " -p" + DB_USER_PASSWORD + " " + db + " > " + pipes.quote(BACKUP_PATH) + "/" + db + ".sql"
   os.system(dumpcmd)
   gzipcmd = "gzip " + pipes.quote(BACKUP_PATH) + "/" + db + ".sql"
   os.system(gzipcmd)
 
print ("")
print ("Database backup script completed, stored in /backup")
print("Zipping WWW")
os.chdir('/backup')
# Zip www 
shutil.make_archive('/backup/WWW', 
                    'zip',
                    '/var/',
                    'www')
# Zipiping everything to s3Stage
os.chdir('/s3Stage')
print("Merging backup to /s3Stage")
shutil.make_archive('/s3Stage/'+today+hostName+'Backup', 
                    'zip',
                    '/',
                    'backup')

# this loads the .env file with our credentials
load_dotenv()

# name of the file and bucket to upload to 
file_name = ''+today+hostName+'Backup.zip' 


# Upload to S3 Bucket
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
)
# os.system('aws s3 cp /s3Stage/'+today+'Backup.zip' 's3://rearview-backups')
response = s3_client.upload_file(file_name, bucket_name, file_name)
print("Backup to S3 Complete")
print("Cleaning up")
shutil.rmtree(BACKUP_PATH)
shutil.rmtree(s3StagingPath)
# Remove Backups older than x 
backupName = str(today+hostName+'Backup'+'.zip')
now = date.today()
retention_target = now - timedelta(days=retention_days)
subString = 'Master-TrackerBackup'
s3 = boto3.resource('s3')

my_bucket = s3.Bucket(bucket_name)

for file in my_bucket.objects.all():
    currentFile = str(file.key)
    if subString in currentFile:
        print("Found!, Checking against retention-date")
        # print(currentFile)
        dateOfFile = datetime.strptime(str(file.last_modified.date()), "%Y-%m-%d").date()
        # print(dateOfFile)
        dateOfTarget = datetime.strptime(str(retention_target), "%Y-%m-%d").date()
        print(dateOfTarget)
        print(dateOfFile)
        
        if (dateOfFile < dateOfTarget):
            print("File is older than target date")
            s3 = boto3.resource("s3")
            obj = s3.Object(bucket_name, file.key)
            print(obj)
            obj.delete()
        else:
            print("File is newer than target date")
   
   
            
    else:
        print("Not a Master-Tracker Backup")
    





print("Done!")
