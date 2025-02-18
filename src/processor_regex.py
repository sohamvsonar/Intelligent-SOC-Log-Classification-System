import re
def regex_classify(log_message):
    regex_patterns = {
        r"User User\d+ logged (in|out).": "User Action",
        r"Backup (started|ended) at .*": "System Notification",
        r"Backup completed successfully.": "System Notification",
        r"System updated to version .*": "System Notification",
        r"File .* uploaded successfully by user .*": "System Notification",
        r"Disk cleanup completed successfully.": "System Notification",
        r"System reboot initiated by user .*": "System Notification",
        r"Account with ID .* created by .*": "User Action"
    }
    for pattern, label in regex_patterns.items():
        if re.search(pattern, log_message, re.IGNORECASE):
            return label
    return None

if __name__ == "__main__":
    print(regex_classify("User User123 logged in."))
    print(regex_classify("Backup started at 2025-01-01 00:00:00."))
    print(regex_classify("Backup completed successfully."))
    print(regex_classify("System updated to version 2.0.5."))
    print(regex_classify("File data_6169.csv uploaded successfully by user User123."))
    print(regex_classify("Disk cleanup completed successfully."))
    print(regex_classify("System reboot initiated by user User123."))
    print(regex_classify("Account with ID 1234 created by User123."))