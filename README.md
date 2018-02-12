# Machine Learning for Solid Waste Management

Install Anaconda Python 3:
- https://www.anaconda.com/download
- https://www.digitalocean.com/community/tutorials/how-to-install-the-anaconda-python-distribution-on-ubuntu-16-04

Install Needed Extra Libraries:
- `pip install --upgrade google-api-python-client`
- `pip install boto3`

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

1. Export the Google Drive Spreadsheet as a csv file
2. Run `./process-csv csv-file-name`

## Authors

* **Andrew Ziegler** - *andrewzieg@gmail.com*
