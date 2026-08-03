import os

from dotenv import load_dotenv


load_dotenv()

GOOGLE_SHEET_WEBHOOK = os.getenv(
    "GOOGLE_SHEET_WEBHOOK",
    "https://script.google.com/macros/s/AKfycbzm1z2UQV0j8ySZr4N7LoeQuqAdHyRKNOJgpnIjGj4D3n1Krph198v0O30mACG-Wu3qpA/exec",
)
