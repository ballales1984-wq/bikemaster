# Configuration settings
import os

# Data settings
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
MOCK_DATA_FILE = os.path.join(DATA_DIR, 'mock_data.json')

# Google Fit API settings (to be configured)
GOOGLE_FIT_CREDENTIALS_FILE = os.getenv('GOOGLE_FIT_CREDENTIALS_FILE', 'credentials.json')
GOOGLE_FIT_TOKEN_FILE = os.getenv('GOOGLE_FIT_TOKEN_FILE', 'token.json')