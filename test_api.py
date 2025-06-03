import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI()  # This will automatically use OPENAI_API_KEY from environment

try:
    # Try to make a simple API call
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Say 'API is working!' if you can read this."}],
        max_tokens=10
    )
    print("Success! API Response:", response.choices[0].message.content)
    print("\nYour API key is working correctly!")
except Exception as e:
    print("Error testing API key:", str(e))
    print("\nTroubleshooting tips:")
    print("1. Check if your API key is correct in the .env file")
    print("2. Make sure the API key starts with 'sk-'")
    print("3. Verify there are no extra spaces or quotes around the API key")
    print("4. Ensure your OpenAI account has billing set up") 