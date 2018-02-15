from flask import Flask, request, redirect, url_for,send_from_directory, render_template_string
from werkzeug.utils import secure_filename
import caffe
import json
import numpy as np
import os
from sklearn import svm
import struct

deployPrototxt = "/opt/caffe/models/bvlc_reference_caffenet/deploy.prototxt"
caffeModel = "/opt/caffe/models/bvlc_reference_caffenet/bvlc_reference_caffenet.caffemodel"
imageDirectory = '/workspace/swm-ml-dataset/images/'
featureVectorDirectory = "/workspace/swm-ml-dataset/CaffeNet-fc7-4096"
metadataDirectory = '/workspace/swm-ml-dataset/metadata/'
imageMeanFile = '/opt/caffe/python/caffe/imagenet/ilsvrc_2012_mean.npy'
layerName = 'fc7'

print("Loading model ...")
cnn = caffe.Net(deployPrototxt, caffe.TEST, weights=caffeModel)
print("Done loading")

# reshape to accept one image at a time.
(_, c, w, h) = cnn.blobs['data'].data.shape
cnn.blobs['data'].reshape(1, c, w, h)
transformer = caffe.io.Transformer({'data': cnn.blobs['data'].data.shape})
transformer.set_mean('data', np.load(imageMeanFile).mean(1).mean(1))
transformer.set_transpose('data', (2,0,1))
transformer.set_raw_scale('data', 255.0)

def loadFeatureVectors(dirPath, d):
    """
    Loads all feature vectors from the local directory into a single nxd matrix
    where n is the number of feature vectors and the d is the dimensionality.
    Returns the matrix and a list of file names in one-to-one correspondence
    with the rows of the matrix.
    """
    allFiles = os.listdir(dirPath)
    data = np.zeros([len(allFiles), d])
    for i, fileName in enumerate(allFiles):
        with open("%s/%s" % (dirPath, fileName), "rb") as inputFile:
            data[i] = struct.unpack('f'*d, inputFile.read())
    return (data, allFiles)

def loadMetaData(metadataDir):
    metadataByImageHash = {}
    allFiles = os.listdir(metadataDir)
    for fileName in allFiles:
        with open("%s/%s" % (metadataDir, fileName), "r") as jsonFile:
            metadata = json.load(jsonFile)
            metadataByImageHash[metadata['Image Hash']] = metadata
    return metadataByImageHash

# Simple case
def makeBinaryLabels(metadataByImageHash, allImageHashes):
    labels = []
    for imageHash in allImageHashes:
        metadata = metadataByImageHash[imageHash]
        labels.append(1 if (metadata['Secondary'] == "NA") else 0)
    return labels

print("Training SVM")
data, allImageHashes = loadFeatureVectors(featureVectorDirectory, d = 4096)
metadataByImageHash = loadMetaData(metadataDirectory)
labels = makeBinaryLabels(metadataByImageHash, allImageHashes)
clf = svm.SVC(probability=True)
clf.fit(data, labels)
print("Finished training ready to classify images")

def getFeatureVector(imageFile):
    cnn.blobs['data'].data[...] = transformer.preprocess('data', caffe.io.load_image(imageFile))
    cnn.forward()
    return cnn.blobs[layerName].data[0]

app = Flask(__name__)

UPLOAD_FOLDER = '/home/ec2-user/demo-uploads'
ALLOWED_EXTENSIONS = set(['jpg', 'jpeg', 'png'])
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit a empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploaded_file',
                                    filename=filename))
    return '''
    <!doctype html>
    <title>Classify Image</title>
    <h1>Choose Image</h1>
    <form method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Classify>
    </form>
    '''

@app.route('/images/<filename>', strict_slashes=False)
def serve_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    imageFile = "%s/%s" % (UPLOAD_FOLDER, filename)
    featureVector = list(getFeatureVector(imageFile))
    d = len(featureVector)
    prob = clf.predict_proba(np.array(featureVector).reshape(1, d))[0, 1]
    return render_template_string('''
    <!doctype html>
    <title>Classify Image</title>
    <h1>Choose Image</h1>
    <form method=post enctype=multipart/form-data action="/">
      <p><input type=file name=file>
         <input type=submit value=Classify>
    </form>
    <h2>Probability of 90% segregated = {{prob}}</h2>
    <img height="600px" src={{url_for('serve_image', filename=filename)}}/>
    ''', filename=filename, prob=prob)

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug = False)
