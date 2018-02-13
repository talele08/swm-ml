import boto3
import os
import sys
import numpy as np
import struct
import caffe

def printUsageAndExit():
    print("Usage: upload-features image-directory caffe-deploy caffe-model mean-image-npy layer-name")
    sys.exit(1)

if len(sys.argv) != 6:
    printUsageAndExit()

imageDirectory = sys.argv[1]
imageMeanFile = sys.argv[4]
layerName = sys.argv[5]

with open(sys.argv[2], 'r') as deployFile:
    firstLine = deployFile.readline()
modelName = firstLine.split(":")[-1].strip().replace('"', '')

print("Loading model %s ..." % modelName)
cnn = caffe.Net(sys.argv[2], caffe.TEST, weights=sys.argv[3])
print("Done loading")

if layerName not in cnn.blobs:
    print("Invalid layer name: %s" % layerName)
    printUsageAndExit()

# reshape to accept one image at a time.
(_, c, w, h) = cnn.blobs['data'].data.shape
cnn.blobs['data'].reshape(1, c, w, h)
transformer = caffe.io.Transformer({'data': cnn.blobs['data'].data.shape})
transformer.set_mean('data', np.load(imageMeanFile).mean(1).mean(1))
transformer.set_transpose('data', (2,0,1))
transformer.set_raw_scale('data', 255.0)

def featureVectorToS3Path(imageHash, modelName, layerName, d):
    return "%s-%s-%s/%s" % (modelName, layerName, d, imageHash)

s3 = boto3.resource('s3')
bucketName = "swm-images"
bucket = s3.Bucket(bucketName)

# https://stackoverflow.com/questions/33842944/check-if-a-key-exists-in-a-bucket-in-s3-using-boto3
def featureVectorFileExists(imageHash, modelName, layerName, d):
    key = featureVectorToS3Path(imageHash, modelName, layerName, d)
    objects = list(bucket.objects.filter(Prefix=key))
    return len(objects) > 0 and objects[0].key == key

# According to https://stackoverflow.com/questions/807863/how-to-output-list-of-floats-to-a-binary-file-in-python
# the fastest way to serialized and deserialize float arrays is struct vs. numpy, pickle, json, csv, etc.
def uploadFeatureVector(imageFile, modelName, layerName, d):
    imageHash = os.path.basename(imageFile).replace(".jpg", "")
    if featureVectorFileExists(imageHash, modelName, layerName, d):
        print("\nSkipping %s" % imageHash)
    else:
        s3Path = featureVectorToS3Path(imageHash, modelName, layerName, d)
        print("Uploading feature vector to %s" % s3Path)
        s3Object = s3.Object(bucketName, s3Path)
        cnn.blobs['data'].data[...] = transformer.preprocess('data', caffe.io.load_image(imageFile))
        cnn.forward()
        featureVector = cnn.blobs[layerName].data[0]
        assert(len(featureVector) == d)
        s3Object.put(Body=struct.pack('f'*d, *featureVector))

allImageFiles = os.listdir(imageDirectory)
d = len(cnn.blobs[layerName].data[0])
for imageFile in allImageFiles:
    uploadFeatureVector("%s/%s" % (imageDirectory, imageFile), modelName, layerName, d)
