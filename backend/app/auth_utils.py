import os
from dotenv import load_dotenv

load_dotenv()

ALLOW_UNAUTHENTICATED_TRAIN = (
    os.getenv("ALLOW_UNAUTHENTICATED_TRAIN", "false").lower() == "true"
)
