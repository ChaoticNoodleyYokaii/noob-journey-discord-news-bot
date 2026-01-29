import discord
from discord.ext import tasks, commands
import os
import json
from dotenv import load_dotenv
from news_fetcher import NewsFetcher
import asyncio

# Carregar variáveis de ambiente
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 3600))
SENT_NEWS_FILE = "sent_news.json"
CONFIG_FILE = "server_config.json"


def load_sent_news():
    if os.path.exists(SENT_NEWS_FILE):
        with open(SENT_NEWS_FILE, "r") as f:
            return json.load(f)
    return []


def save_sent_news(sent_list):
    with open(SENT_NEWS_FILE, "w") as f:
        json.dump(sent_list[-100:], f, indent=4)


def load_configs():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("Erro ao ler server_config.json, usando config vazia.")
            return {}
    return {}


def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=4)


class NewsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True

        super().__init__(command_prefix="!", intents=intents)

        self.fetcher = NewsFetcher()
        self.sent_news = load_sent_news()
        self.configs = load_configs()  #ServerConfig

    async def setup_hook(self):
        self.check_news.start()

    async def on_ready(self):
        print(f"Bot conectado como {self.user}")

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_news(self):

        for guild_id, config in self.configs.items():

            channel_id = config.get("channel_id")
            if not channel_id:
                continue

            channel = self.get_channel(channel_id)
            if not channel:
                print(f"Canal {channel_id} não encontrado.")
                continue

            categories = []
            if config.get("windows"):
                categories.append("windows")
            if config.get("linux"):
                categories.append("linux")

            for category in categories:
                news_items = self.fetcher.fetch_latest_news(category)

                for item in reversed(news_items):
                    if item["id"] not in self.sent_news:
                        await self.post_news(channel, item)
                        self.sent_news.append(item["id"])
                        save_sent_news(self.sent_news)
                        await asyncio.sleep(5)

    async def post_news(self, channel, item):
        color = discord.Color.blue() if item["category"] == "windows" else discord.Color.orange()

        embed = discord.Embed(
            title=item["title"],
            url=item["link"],
            description=item["summary"],
            color=color
        )

        if item["image_url"]:
            embed.set_image(url=item["image_url"])

        embed.set_footer(text=f"Fonte: {item['category'].capitalize()} | {item['published']}")

        await channel.send(embed=embed)


bot = NewsBot()


@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    guild_id = str(ctx.guild.id)

    if guild_id not in bot.configs:
        bot.configs[guild_id] = {}

    bot.configs[guild_id]["channel_id"] = ctx.channel.id
    bot.configs[guild_id]["windows"] = True
    bot.configs[guild_id]["linux"] = True

    save_configs(bot.configs)

    await ctx.send(f"Canal de notícias configurado: {ctx.channel.mention}")


if __name__ == "__main__":
    if not TOKEN:
        print("Erro: DISCORD_TOKEN não configurado.")
    else:
        bot.run(TOKEN)
