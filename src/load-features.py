import os
import numpy as np
import struct

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
