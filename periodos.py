"""Vocabulário e resolução temporal compartilhados entre os executores."""
import re
from datetime import timedelta

MONTHS = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".replace("ç","c").split()

YEAR_NOW = r"(?:(?:(?:n|d)?este|(?:n|d)?esse) ano|ano (?:atual|corrente)|ano em curso)"
YEAR_LAST = r"(?:ano (?:passado|anterior)|ultimo ano civil)"
MONTH_NOW = r"(?:(?:(?:n|d)?este|(?:n|d)?esse) mes|mes atual)"
MONTH_LAST = r"(?:ultimo mes|mes passado|mes anterior)"
YEAR_NUMBER = r"(?:19|20)\d{2}"
MONTH_NAME = "(?:" + "|".join(MONTHS) + ")"
PERIOD_TOKEN = rf"\b(?:{YEAR_NOW}|{YEAR_LAST}|{MONTH_NOW}|{MONTH_LAST}|{YEAR_NUMBER}|{MONTH_NAME})\b"

def calendar_period(question, previous, today):
    # Remove bill references: their year identifies a bill rather than a reporting period.
    text = re.sub(r"\b[a-z]{2,6}\s*\d+\s*/\s*\d{4}\b", "", question)
    year = re.search(rf"\b{YEAR_NUMBER}\b",text)
    named = re.search(rf"\b{MONTH_NAME}\b",text)
    if year:
        year = int(year[0])
    elif re.search(rf"\b{YEAR_NOW}\b",text):
        year = today.year
    elif re.search(rf"\b{YEAR_LAST}\b",text):
        year = today.year - 1
    if named:
        month = MONTHS.index(named[0])+1
        return year or previous.get("ano") or today.year-int(month>today.month), month
    if previous.get("ano") and re.search(r"\b(nesse mesmo mes|nesse mes|desse mes|mesmo mes)\b",text):
        return previous["ano"],previous.get("mes",0)
    for pattern, day in ((MONTH_LAST,today.replace(day=1)-timedelta(days=1)), (MONTH_NOW,today)):
        if re.search(rf"\b{pattern}\b",text):
            return year or day.year, day.month
    return (year,0) if year else None

def is_period_reply(question):
    if not re.search(PERIOD_TOKEN,question):
        return False
    rest = re.sub(PERIOD_TOKEN," ",question)
    return not re.sub(r"\b(?:agora|e|em|no|na|de|do|mes|ano|durante|todo|o|por|favor)\b|[\s,.?!]","",rest)

