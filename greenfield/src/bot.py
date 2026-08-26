from greenfieldbot.config import Config
from greenfieldbot.discord_bot import create_bot


def main():
    Config.validate()

    bot = create_bot()

    bot.run(Config.discord_bot)


if __name__ == "__main__":
    main()
