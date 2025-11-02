# tamucc-ai-hackathon
ai project for the hackathon
------------------------------------------------
Team: Sea Snakes
Members: Austin Vu, Asher Taylor, Joshue Bockerstette, Roy Hurt

Project: HealthNav AI 

We wanted to make a software that helps people find the best health care for what they needed.

------------------------------------------------

HealthNav AI is a project for the TAMUCC AI 2025 hackathon designed to utilize AI for good. It is a website
(for now only on localhost) that users can go to if they have a medical issue. Users input their condition and the 
AI powered by ChatGPT recommends users the best hospitals that are close and are the most equipped to handle them

This project uses:
------------------------------------------------ 
- Languages: Python, JavaScript, CSS, HTML, SQL

- Bun

- MariaDB

- GPT 4 via API

- pip

Instructions/Tips to get started:
---------------------------------------------------- 
python3 -m venv venv
source venv/bin/activate
to load initial dataset:
mysql -u root -p your_database_name < dataset.sql
CREATE USER 'webuser'@'localhost' IDENTIFIED BY 'REMOVED_PASSWORD';
bunx serve --listen 8000
python3 healthserver.py

Docs:
--------------------------------------------------
https://bun.com/docs/installation
https://mariadb.org/download/
------------------------------------------------
future plans:
We would implement voice recognition and directions on the map 
