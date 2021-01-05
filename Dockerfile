# Based on Python
FROM python:alpine

LABEL Name=list_parser_bot Version=0.0.1

# Copy all files in listparser as well as requirements.txt to the working directory of the container filesystem.
WORKDIR /listparser
COPY listparser .
COPY requirements.txt .

# Using pip:
RUN python3 -m pip install -r requirements.txt

# Start bot
CMD ["python3", "-u", "./parse_article_archives.py"]