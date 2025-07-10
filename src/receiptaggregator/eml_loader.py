import os
import re
from email.parser import BytesParser
from email.policy import default

from lxml.html.clean import Cleaner

link_regex = re.compile(r"https?://\S+|www\.\S+")
html_regex = re.compile(r"<(!--)?(?!\s|>)[^>]*>")
cleaner = Cleaner(
    style=True,
    scripts=True,
    comments=True,
    javascript=True,
    page_structure=True,
    safe_attrs_only=True,
)


def parse_eml(eml_file: str) -> dict | None:
    """Parse an eml file and return a dictionary of the email.
    :param eml_file: The path to the eml file.
    """
    with open(eml_file, "rb") as f:
        msg = BytesParser(policy=default).parse(f)
    body = ""

    # Note: Currently forwarded emails break the logic for datetime.
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                body += part.get_payload(decode=True).decode(charset)
            elif part.get_content_type() == "text/html":
                # In the current approach, we can just add html as some html gets caught in normal text/plain anyways.
                # so we can just prune it all at once.
                charset = part.get_content_charset() or "utf-8"
                body += part.get_payload(decode=True).decode(charset)
    else:
        body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8")
    # Remove all html that we can.
    email = {"Subject": msg["Subject"], "From": msg["From"], "Date": msg["Date"]}
    clean_body = cleaner.clean_html(body)
    clean_body = html_regex.sub(r"", link_regex.sub(r"", clean_body))
    # Remove big spaces left behind
    clean_body = re.sub(r"(\n\s*){2,}", "\n", clean_body)
    email["Body"] = clean_body
    # Parse out all of the links and any remaining html so that everything else can happen faster.
    return email


def parse_directory(directory: str) -> list[dict]:
    """Parse all of the emails in a directory and return a list of dictionaries of the emails.
    :param directory: The path of the  directory to parse.
    """
    parsed_emails = []
    total = 0
    for file in os.listdir(directory):
        if file.endswith(".eml"):
            parsed_email = parse_eml(os.path.join(directory, file))
            if parsed_email is not None:
                total += len(parsed_email["Body"])
                parsed_emails.append(parsed_email)
    return parsed_emails
