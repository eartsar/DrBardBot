## What is this?
It's a discord bot for the Unofficial DragonRealms Bard Server

## Requirements
In addition to python 3.8+, this bot uses third party services.

The data used by this bot is persisted to a Google Sheets spreadsheet. In order to integrate with this, a google application with a service account is needed. This can be done [here](https://console.developers.google.com/).

## I want to run it.
1. [Make a bot account for Discord.](https://discordpy.readthedocs.io/en/latest/discord.html)
2. Install the requirements. This project uses [poetry](https://python-poetry.org/), and includes a `pyproject.toml` file (`poetry install`).
3. Edit the `config.yml` file, and configure as needed.
4. Run it
`python3 app.py --config /path/to/config.yml`


