import json
import os
import collections
import numpy
import pandas
import sys



def printUsageAndExit():
    print("Usage: metadatasquaregen  metadata-folder-path")
    sys.exit(1)

if len(sys.argv)!=2:
    printUsageAndExit()	

path=sys.argv[1]	

def loadMetaData(metadataDir):
    metadataByImageHash = {}
    allImageHashes=[]
    allFiles = os.listdir(metadataDir)
    for fileName in allFiles:
        with open("%s/%s" % (metadataDir, fileName), "r") as jsonFile:
            metadata = json.load(jsonFile)
            allImageHashes.append(metadata['Image Hash'])
            metadataByImageHash[metadata['Image Hash']] = metadata
    return metadataByImageHash,allImageHashes

classIdByLabel = {"Dry" : 0, "Wet" : 1, "Reject" : 2, "Garden" : 3,"NA" : 4}

# Simple case
def makeBinaryLabels(metadataByImageHash, allImageHashes):
    #labels = []
    labels=numpy.zeros((4,5,5))
    for imageHash in allImageHashes:
        metadata = metadataByImageHash[imageHash]
        #labels.append(metadata['Primary'])
        #labels.append(classIdByLabel[metadata['Primary']])
        idx1=classIdByLabel[metadata['Primary']]
        idx2=classIdByLabel[metadata['Secondary']]
        idx3=classIdByLabel[metadata['Tertiary']]
        labels[idx1][idx2][idx3]+=1
    return labels


metadataByImageHash,allImageHashes=loadMetaData(path)
labels=makeBinaryLabels(metadataByImageHash,allImageHashes)

print "In every matrix Secondary is represented by row and Tertiary by column"
row_labels=["Dry","Wet","Reject","Garden","NA"]
matrix_labels=["Dry","Wet","Reject","Garden"]
for i in range(0,4):
 print "Primary: "+matrix_labels[i]
 df = pandas.DataFrame(labels[i,:,:], columns=row_labels, index=row_labels)
 print df
 print ''


print "Table based only on Primary and Secondary classification: "
Primary_Secondary_matrix=labels.sum(2)
df = pandas.DataFrame(Primary_Secondary_matrix, columns=row_labels, index=matrix_labels)
print df



