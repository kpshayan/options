from dhanhq import DhanContext, dhanhq 
import os
from dotenv import load_dotenv

load_dotenv()

# Default fetch interval in seconds
DEFAULT_FETCH_INTERVAL = 30

#Load env variables
CLIENT_ID = os.getenv("CLIENT_ID")
DHAN_API_TOKEN = os.getenv("DHAN_API_TOKEN")
UNDER_SECURITY_ID = 13
UNDER_EXCHANGE_SEGMENT = "IDX_I"
UNDER_INSTRUMENT_TYPE="INDEX"
UNDER_INTERVAL=1
OHLC_DAYS = 7 #Need to change after testing 15mins, 5mins trend data

# Initialize DhanHQ client
dhan_context = DhanContext(CLIENT_ID,DHAN_API_TOKEN)
dhan = dhanhq(dhan_context)

