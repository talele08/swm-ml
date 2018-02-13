# Machine Learning for Solid Waste Management

Install Anaconda Python 3:
- https://www.anaconda.com/download
- https://www.digitalocean.com/community/tutorials/how-to-install-the-anaconda-python-distribution-on-ubuntu-16-04

Install Needed Extra Libraries:
- `pip install --upgrade google-api-python-client`
- `pip install boto3`
- `pip install awscli --upgrade --user`

Install Docker and the caffe docker image:
- `sudo apt-get install docker.io`
- `docker run -ti bvlc/caffe:cpu caffe --version`

Make sure your AWS credentials are setup:

Setup `~/.aws/credentials` with your key and secret:
  ```
  [default]
  aws_access_key_id = YOUR_KEY
  aws_secret_access_key = YOUR_SECRET
  ```

Set the default region in `~/.aws/config`:
  ```
  [default]
  region=ap-south-1
  ```

## Updating the dataset

1. Export the Google Drive Spreadsheet as a csv file
2. Run `./process-csv csv-file-name`
3. Run `./package-dataset output-folder-path`

Use the flag -f to force syncing with Google drive otherwise cached local
copies will be used if available.

## Downloading and Packaging the Dataset
1. Run `./package-dataset directory-to-store-tarball`

This will create a folder in your home directory called 'swm-ml-dataset'
and save a tarball to the folder you specify.

## Extracting Caffe Features

1. sudo docker run -ti -v ~/swm-ml-dataset/images:/opt/caffe/swm-ml-dataset -v /home/ubuntu/swm-ml:/opt/caffe/swm-ml bvlc/caffe:cpu /bin/bash


## Authors

* **Andrew Ziegler** - *andrewzieg@gmail.com*
