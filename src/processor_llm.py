from dotenv import load_dotenv
from groq import Groq
import re

load_dotenv()

groq = Groq()

def llm_classify(log_msg):
    """
    Generate a variant of the input sentence. For example,
    If input sentence is "User session timed out unexpectedly, user ID: 9250.",
    variant would be "Session timed out for user 9251"
    """
    prompt = f'''Classify the log message into one of these categories: 
    (1) Workflow Error, (2) Deprecation Warning.
    If you can't figure out a category, use "Unclassified".
    Put the category inside <category> </category> tags. 
    Log message: {log_msg}'''

    chat_completion = groq.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        # model="llama-3.3-70b-versatile",
        model="deepseek-r1-distill-llama-70b",
        temperature=0.5
    )

    content = chat_completion.choices[0].message.content
    match = re.search(r'<category>(.*)<\/category>', content, flags=re.DOTALL)
    category = "Unclassified"
    if match:
        category = match.group(1)

    return category


if __name__ == "__main__":
    logs = [
        "alpha.osapi_compute.wsgi.server - 12.10.11.1 - API returned 404 not found error",
        "GET /v2/3454/servers/detail HTTP/1.1 RCODE   404 len: 1583 time: 0.1878400",
        "System crashed due to drivers errors when restarting the server",
        "Hello World",
        "Multiple login failures occurred on user 6454 account",
        "Server A790 was restarted unexpectedly during the process of data transfer"
    ]
    for log in logs:
        label = llm_classify(log)
        print(log, "->", label)
