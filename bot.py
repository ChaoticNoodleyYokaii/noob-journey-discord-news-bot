import discord
from discord.ext import tasks, commands
import os
import json
from dotenv import load_dotenv
from news_fetcher import NewsFetcher
import asyncio

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
        json.dump(sent_list[-200:], f, indent=4)


def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=4)


class NewsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True

        super().__init__(
            command_prefix="/",
            intents=intents,
            help_command=None
        )

        self.fetcher = NewsFetcher()
        self.sent_news = load_sent_news()
        self.configs = load_configs()

        self.status_list = [
            "Lendo RSS",
            "Compilando Kernel",
            "Atualizando o Windows",
            "Servindo notícias quentinhas ☕",
            "/help"
        ]
        self.status_index = 0

    async def setup_hook(self):
        print("📦 Carregando cogs...")

        for file in os.listdir("./cogs"):
            if file.endswith(".py"):
                await self.load_extension(f"cogs.{file[:-3]}")
                print(f"✅ Cog carregado: {file}")

        await self.tree.sync()
        print("✅ Slash commands sincronizados")

        self.check_news.start()
        self.rotate_status.start()

    async def on_ready(self):
        print(f"✅ Bot conectado como {self.user}")

    @tasks.loop(seconds=60)
    async def rotate_status(self):
        await self.wait_until_ready()
        activity = discord.Game(name=self.status_list[self.status_index])
        await self.change_presence(activity=activity)
        self.status_index = (self.status_index + 1) % len(self.status_list)

    @tasks.loop(seconds=CHECK_INTERVAL)
    async def check_news(self):
        await self.wait_until_ready()

        for guild_id, config in list(self.configs.items()):
            channel_id = config.get("channel_id")
            if not channel_id:
                continue

            try:
                channel = await self.fetch_channel(channel_id)
            except Exception as e:
                print(f"Erro ao buscar canal: {e}")
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
                        await self.post_news(channel, item, guild_id)
                        self.sent_news.append(item["id"])
                        save_sent_news(self.sent_news)
                        await asyncio.sleep(5)

    async def post_news(self, channel, item, guild_id):
        config = self.configs.get(str(guild_id), {})
        roles = config.get("roles", {})
        role_ids = roles.get(item["category"], [])
        role_mentions = " ".join(f"<@&{rid}>" for rid in role_ids)

        color = discord.Color.blue() if item["category"] == "windows" else discord.Color.orange()

        embed = discord.Embed(
            title=item["title"],
            url=item["link"],
            description=item["summary"],
            color=color
        )

        if item.get("image_url"):
            embed.set_image(url=item["image_url"])

        embed.set_footer(text=f"Fonte: {item['category']} | {item['published']}")

        await channel.send(
            content=f"🔔 **Breaking News!** {role_mentions}",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )


bot = NewsBot()


if __name__ == "__main__":
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado")
    else:
        bot.run(TOKEN)
