import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()
client = genai.Client(api_key=os.getenv("LLM_API_KEY"))

for attempt in range(1, 5):
    try:
        reply = client.models.generate_content(
            model=os.getenv("LLM_MODEL"),
            contents="Say hello in one sentence."
        )
        print(reply.text)
        break
    except errors.ServerError as e:
        print(f"Attempt {attempt} failed (server busy). Retrying...")
        time.sleep(5 * attempt)
else:
    print("Still unavailable. Try again later or switch model.")