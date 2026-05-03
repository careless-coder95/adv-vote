import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Required variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Optional variables (with default fallback)
WELCOME_IMAGE_URL = os.getenv(
    "WELCOME_IMAGE_URL",
    "https://files.catbox.moe/fuk9w5.jpg"
)

SUPPORT_URL = os.getenv(
    "SUPPORT_URL",
    "https://t.me/CarelessxWorld"
)

UPDATE_URL = os.getenv(
    "UPDATE_URL",
    "https://t.me/ll_CarelessxCoder_ll"
)

OWNER_URL = os.getenv(
    "OWNER_URL",
    "https://t.me/CarelessxOwner"
)
