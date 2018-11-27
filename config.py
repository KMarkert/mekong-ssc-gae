import ee

# The service account email address authorized by your Google contact.
# Set up a service account as described in the README.
EE_ACCOUNT = '<YOUR_SERVICE_ACCOUNT>'

# The private key associated with your service account in Privacy Enhanced
# Email format (.pem suffix).  To convert a private key from the RSA format
# (.p12 suffix) to .pem, run the openssl command like this:
# openssl pkcs12 -in downloaded-privatekey.p12 -nodes -nocerts > privatekey.pem
EE_PRIVATE_KEY_FILE = '<PATH_TO_CREDENTIAL>'

EE_CREDENTIALS = ee.ServiceAccountCredentials(EE_ACCOUNT, EE_PRIVATE_KEY_FILE)
