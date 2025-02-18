from dotenv import load_dotenv
from groq import Groq

load_dotenv()

groq = Groq()

def llm_classify(log_message):
    prompt = f''' Classify the log message "{log_message}" into one of the following categories:
    1. HTTP Status
    2. Critical Error
    3. Security Alert
    4. System Notification
    5. User Action.
    6. Workflow Error
    If you cannot determine the category, return Unclassified.
    Only return the category name. Do not return any other text.

    '''
    chat_completion = groq.chat.completions.create(
        model="deepseek-r1-distill-llama-70b",
        messages=[
            {"role": "user", "content": prompt},
        ])

    return chat_completion.choices[0].message.content

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
