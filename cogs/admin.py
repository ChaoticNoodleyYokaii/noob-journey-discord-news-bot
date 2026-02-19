import discord
from discord import app_commands
from discord.ext import commands
import json
import os

CONFIG_FILE = "server_config.json"


def load_configs():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}


def save_configs(configs):
    with open(CONFIG_FILE, "w") as f:
        json.dump(configs, f, indent=4)


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.configs = load_configs()

    # ================= SETROLE =================
    @app_commands.command(name="setrole", description="Adiciona um cargo para uma categoria")
    @app_commands.describe(category="windows ou linux", role="Cargo a ser adicionado")
    @app_commands.checks.has_permissions(administrator=True)
    async def setrole(self, interaction: discord.Interaction, category: str, role: discord.Role):
        category = category.lower()

        if category not in ["windows", "linux"]:
            await interaction.response.send_message("Use `windows` ou `linux`.", ephemeral=True)
            return

        gid = str(interaction.guild.id)

        self.configs.setdefault(gid, {})
        self.configs[gid].setdefault("roles", {})
        self.configs[gid]["roles"].setdefault(category, [])

        if role.id in self.configs[gid]["roles"][category]:
            await interaction.response.send_message("Esse cargo já está configurado.", ephemeral=True)
            return

        self.configs[gid]["roles"][category].append(role.id)
        save_configs(self.configs)

        await interaction.response.send_message(
            f"✅ Cargo {role.mention} adicionado para **{category}**.",
            ephemeral=True
        )

    # ================= REMOVEROLE =================
    @app_commands.command(name="removerole", description="Remove um cargo de uma categoria")
    @app_commands.describe(category="windows ou linux", role="Cargo a ser removido")
    @app_commands.checks.has_permissions(administrator=True)
    async def removerole(self, interaction: discord.Interaction, category: str, role: discord.Role):
        category = category.lower()
        gid = str(interaction.guild.id)

        if category not in ["windows", "linux"]:
            await interaction.response.send_message("Use `windows` ou `linux`.", ephemeral=True)
            return

        roles = self.configs.get(gid, {}).get("roles", {}).get(category, [])

        if role.id not in roles:
            await interaction.response.send_message("Esse cargo não está configurado.", ephemeral=True)
            return

        roles.remove(role.id)
        save_configs(self.configs)

        await interaction.response.send_message(
            f"🗑️ Cargo {role.mention} removido de **{category}**.",
            ephemeral=True
        )

    # ================= SHOWROLES =================
    @app_commands.command(name="showroles", description="Mostra os cargos configurados")
    async def showroles(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)
        roles_cfg = self.configs.get(gid, {}).get("roles", {})

        if not roles_cfg:
            await interaction.response.send_message("Nenhum cargo configurado.", ephemeral=True)
            return

        msg = "🎭 **Cargos configurados:**\n\n"

        for category, role_ids in roles_cfg.items():
            role_mentions = []
            for rid in role_ids:
                role = interaction.guild.get_role(rid)
                if role:
                    role_mentions.append(role.mention)

            roles_text = " ".join(role_mentions) if role_mentions else "Nenhum"
            msg += f"**{category.capitalize()}**: {roles_text}\n"

        await interaction.response.send_message(msg, ephemeral=True)

        # ================= CLEARROLES =================
    @app_commands.command(name="clearroles", description="Remove todos os cargos configurados")
    @app_commands.checks.has_permissions(administrator=True)
    async def clearroles(self, interaction: discord.Interaction):
        gid = str(interaction.guild.id)

        if gid in self.configs and "roles" in self.configs[gid]:
            self.configs[gid]["roles"] = {}
            save_configs(self.configs)

            await interaction.response.send_message(
                "🧹 Todos os cargos foram removidos.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Nenhum cargo configurado.",
                ephemeral=True
            )


# 🔽 ESSENCIAL: registrar o Cog
async def setup(bot):
    await bot.add_cog(Admin(bot))
