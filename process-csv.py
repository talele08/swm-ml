from apiclient import discovery
from googleapiclient.http import MediaIoBaseDownload
from oauth2client.file import Storage
import boto3
import csv
import hashlib
import httplib2
import io
import json
import os
import sys

def initGoogleDriveService():
    store = Storage("./credentials.json")
    credentials = store.get()
    service = discovery.build('drive', 'v3', http=credentials.authorize(httplib2.Http()))
    return service

if len(sys.argv) != 2:
    print("Usage: process-csv csv-file-path")
    sys.exit(1)

csvFilePath = sys.argv[1]
print("Will process csv file %s" % csvFilePath)

service = initGoogleDriveService()

print("Loading all folder locations from Google Drive ...")
allFolders = service.files().list(q="mimeType='application/vnd.google-apps.folder'").execute()['files']
print("Finished loading locations")

def getParent(service, fileId):
    try:
        parents = service.files().get(fileId=fileId, fields="parents").execute()['parents']
        assert(len(parents) == 1)
        return parents[0]
    except KeyError:
        return None

print("Building file id to parent map ...")
parentByFileId = {}
folderNameByFileId = {}
for folder in allFolders:
    fileId = folder['id']
    folderNameByFileId[fileId] = folder['name']
    parentByFileId[fileId] = getParent(service, fileId)
print("Finished building parent map")

def findRootFileId(parentByFileId):
    result = [fileId for fileId, parentId in parentByFileId.items() if parentId is None]
    assert(len(result) == 1)
    return result[0]
    
def buildPathToFileIdMap(parentByFileId, folderNameByFileId):
    rootFileId = findRootFileId(parentByFileId)
    fileIdToPath = { rootFileId : folderNameByFileId[rootFileId] }
    del parentByFileId[rootFileId]
    while len(parentByFileId) > 0:
        haveKnownParent = [(fileId, parentId) for fileId, parentId in parentByFileId.items() if parentId in fileIdToPath]
        for fileId, parentId in haveKnownParent:
            fileIdToPath[fileId] = "%s/%s" % (fileIdToPath[parentId], folderNameByFileId[fileId])
            del parentByFileId[fileId]
    pathToFileId = {v:k for k,v in fileIdToPath.items()}
    assert(len(pathToFileId) == len(fileIdToPath))
    return pathToFileId

print("Building map from folder path to file id ...")
pathToFileId = buildPathToFileIdMap(parentByFileId.copy(), folderNameByFileId)
print("Finished building path map")

prefix = 'ML Project/ML Waste mgmt Images'
def imagePathToFileId(parentFolder, fileName):
    parentFileId = pathToFileId['%s/%s' % (prefix, parentFolder)]
    return imageFileNameToFileId(service, parentFileId, fileName)

def imageFileNameToFileId(service, parentFileId, fileName):
    query = "name='%s' and '%s' in parents" % (fileName, parentFileId)
    allFiles = service.files().list(q=query).execute()['files']
    assert(len(allFiles) == 1)
    return allFiles[0]['id']

# Copied from https://developers.google.com/drive/v3/web/manage-downloads
def downloadImageFile(drive_service, file_id):
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh

s3 = boto3.resource('s3')
bucketName = "swm-images"
bucket = s3.Bucket(bucketName)

def fileIdToS3Path(fileId):
    return "%s/%s.json" % ("metadata", fileId)

def imageHashToS3Path(imageHash):
    return "%s/%s.jpg" % ("images", imageHash)

# https://stackoverflow.com/questions/33842944/check-if-a-key-exists-in-a-bucket-in-s3-using-boto3
def jsonFileExists(fileId):
    key = fileIdToS3Path(fileId)
    objects = list(bucket.objects.filter(Prefix=key))
    return len(objects) > 0 and objects[0].key == key

def uploadJsonFile(fileId, contents):
    s3Path = fileIdToS3Path(fileId)
    print("Uploading metadata to %s" % s3Path)
    s3Object = s3.Object(bucketName, s3Path)
    s3Object.put(Body=str.encode(contents))

def uploadImageFile(imageHash, imageBytes):
    s3Path = imageHashToS3Path(imageHash)
    print("Uploading image to %s" % s3Path)
    s3Object = s3.Object(bucketName, s3Path)
    s3Object.put(Body=imageBytes)

headerRow = ['Serial No', 'Primary', 'Secondary', 'Tertiary', 'Source', 'Photographer', 'Receptacle', 'Lining', 'Image Name']
columnNameToIdx = {name:idx for idx, name in enumerate(headerRow) }

def imageBytesToHash(imageBytes):
    m = hashlib.sha256()
    m.update(imageBytes)
    imageHash = m.hexdigest()
    return imageHash

def rowToJson(row, fileId, filePath, imageHash, imagePath):
    d = dict(zip(headerRow, row))
    d["Image Hash"] = imageHash
    d["SpreadSheet File"] = filePath
    d["Logical Path"] = imagePath
    d["Google File Id"] = fileId
    return json.dumps(d)

def processRow(service, filePath, row):
    imageFileName = row[columnNameToIdx['Image Name']]
    parentFolderName = row[columnNameToIdx['Photographer']]
    fileId = imagePathToFileId(parentFolderName, imageFileName)
    imagePath = "/%s/%s/%s" % (prefix, parentFolderName, imageFileName)
    if jsonFileExists(fileId):
        print("Skipping %s since it was already processed" % imagePath)
    else:
        print("Downloading %s" % imagePath)
        imageFileHandle = downloadImageFile(service, fileId)
        imageBytes = imageFileHandle.getvalue()
        imageHash = imageBytesToHash(imageBytes)
        uploadImageFile(imageHash, imageBytes)
        jsonContents = rowToJson(row, fileId, filePath, imageHash, imagePath)
        uploadJsonFile(fileId, jsonContents)
    print("Finished Processing %s" % imagePath)

def processSpreadSheet(service, filePath):
    print("Processing %s" % filePath)
    with open(filePath, 'r') as csvfile:
        csvReader = csv.reader(csvfile)
        rows = [row for row in csvReader]
        assert(rows[0] == headerRow)
        for row in rows[1:]:
            processRow(service, filePath, row)
    print("Finished processing %s" % filePath)

processSpreadSheet(service, csvFilePath)
