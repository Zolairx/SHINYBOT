import discord
from discord.ext import commands
from discord import app_commands
import os
import sqlite3
import asyncio
import enum
from datetime import datetime
from flask import Flask
import threading

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents, voice_client_cls=None)


GUILD_ID = 126311965126688769  # ID du serveur Discord

# Connexion SQLite
conn = sqlite3.connect('shinybot.db')
cursor = conn.cursor()

# Création de la table shiny si elle n'existe pas
cursor.execute("""
CREATE TABLE IF NOT EXISTS shiny (
    user_id TEXT,
    pokemon TEXT,
    methode TEXT,
    odds TEXT,
    date TEXT,
    points INTEGER
)
""")
conn.commit()

ROLE_IDS = {
    "SHINY_HUNTER_1": 1391093500275195945,
    "SHINY_MASTER": 1391093852588212374,
    "SHINY_DE_PLATINE": 1391094062626508841,
    "SHINY_D_OR": 1391094317736661003,
    "SHINY_D_ARGENT": 1391095112930426995,
    "SHINY_NOVICE": 1391094499786100736,
}

class MethodeEnum(enum.Enum):
    Full_Odds_1_8192 = "Full Odds 1/8192"
    Full_Odds_Herbes_double_1_8192 = "Full Odds Herbes double 1/8192"
    Full_Odds_1_4096 = "Full Odds 1/4096"
    Full_Odds_Herbes_double_1_4096 = "Full Odds Herbes double 1/4096"
    Starter_HG_SS_Casino = "Starter HG/SS & Casino ALL GEN 1/8192"
    Charme_Chroma_2370_5G = "Charme Chroma (1/2370) 5G"
    Charme_Chroma_1365 = "Charme Chroma (1/1365)"
    Masuda_5G = "Masuda 5G"
    Hordes_sans_Charme_PokeRadar = "Hordes sans Charme Chroma/Pokéradar Full Odds"
    Hordes_Charme_Chroma = "Hordes Charme Chroma"
    Methode_PR_Peche_SOS_Navidex = "Méthode (PR/Péche à la chaîne/SOS/Navidex etc...)"
    Legendes_Arceus = "Légendes Arceus"
    Pokemon_Violet_Full_Odds = "Pokémon Violet Écarlate Full Odds"
    Charme_Chroma_Violet = "Charme Chroma Violet Écarlate"
    Sandwich_Shiny_AM = "Sandwich Shiny/Apparition massive"

class OddsEnum(enum.Enum):
    Normal = "Normal"
    Switch_2 = "Switch 2"

def calculate_points(methode, odds):
    points = 0
    if methode == "Full Odds 1/8192":
        points = 50
    elif methode == "Full Odds Herbes double 1/8192":
        points = 25
    elif methode == "Full Odds 1/4096":
        points = 25
    elif methode == "Full Odds Herbes double 1/4096":
        points = 12
    elif methode == "Starter HG/SS & Casino ALL GEN 1/8192":
        points = 15
    elif methode == "Charme Chroma (1/2370) 5G":
        points = 15
    elif methode == "Charme Chroma (1/1365)":
        points = 10
    elif methode == "Masuda 5G":
        points = 5
    elif methode == "Hordes sans Charme Chroma/Pokéradar Full Odds":
        points = 5
    elif methode == "Hordes Charme Chroma":
        points = 3
    elif methode == "Méthode (PR/Péche à la chaîne/SOS/Navidex etc...)":
        points = 2
    elif methode == "Légendes Arceus":
        points = 1
    elif methode == "Pokémon Violet Écarlate Full Odds":
        points = 4
    elif methode == "Charme Chroma Violet Écarlate":
        points = 2
    elif methode == "Sandwich Shiny/Apparition massive":
        points = 1

    if odds == "Switch 2":
        points = points / 2

    return int(points)

def add_shiny(user_id, pokemon, methode, odds, date, points):
    cursor.execute(
        "INSERT INTO shiny (user_id, pokemon, methode, odds, date, points) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, pokemon, methode, odds, date, points)
    )
    conn.commit()
    return points

def get_ladder():
    cursor.execute("""
    SELECT user_id, SUM(points) as total_points
    FROM shiny
    GROUP BY user_id
    ORDER BY total_points DESC
    """)
    return cursor.fetchall()

async def update_roles():
    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        print("Guild non trouvée")
        return

    ladder = get_ladder()
    position = 1
    for user_id, _ in ladder:
        member = guild.get_member(int(user_id))
        if member is None:
            position += 1
            continue

        if position == 1:
            role_id = ROLE_IDS["SHINY_HUNTER_1"]
        elif 2 <= position <= 5:
            role_id = ROLE_IDS["SHINY_MASTER"]
        elif 6 <= position <= 15:
            role_id = ROLE_IDS["SHINY_DE_PLATINE"]
        elif 16 <= position <= 25:
            role_id = ROLE_IDS["SHINY_D_OR"]
        elif 26 <= position <= 35:
            role_id = ROLE_IDS["SHINY_D_ARGENT"]
        else:
            role_id = ROLE_IDS["SHINY_NOVICE"]

        roles_to_remove = [guild.get_role(rid) for rid in ROLE_IDS.values()]
        roles_to_remove = [r for r in roles_to_remove if r is not None]

        for r in roles_to_remove:
            if r in member.roles and r.id != role_id:
                await member.remove_roles(r)

        role = guild.get_role(role_id)
        if role not in member.roles:
            await member.add_roles(role)

        position += 1

async def background_role_updater():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await update_roles()
        except Exception as e:
            print(f"Erreur update_roles: {e}")
        await asyncio.sleep(60)  # Mise à jour toutes les 60 secondes

@bot.event
async def on_ready():
    print(f"Connecté en tant que {bot.user}")
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    print(f"Commandes synchronisées sur le serveur {GUILD_ID}")
    bot.loop.create_task(background_role_updater())

@bot.tree.command(
    name="shiny_ajout",
    description="Ajouter un shiny au ladder. Méthodes et Odds disponibles dans les choix.",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    pokemon="Nom du Pokémon shiny",
    methode="Méthode de shiny hunting",
    odds="Odds spéciaux"
)
@app_commands.choices(
    methode=[app_commands.Choice(name=m.value, value=m.value) for m in MethodeEnum],
    odds=[app_commands.Choice(name=o.value, value=o.value) for o in OddsEnum]
)
async def shiny_ajout(interaction: discord.Interaction, pokemon: str, methode: str, odds: str):
    date_obj = datetime.now()
    date_formatted = date_obj.strftime("%d-%m-%Y")

    points = calculate_points(methode, odds)
    add_shiny(str(interaction.user.id), pokemon, methode, odds, date_formatted, points)

    embed = discord.Embed(
        title="✨ Nouveau Shiny Ajouté ! ✨",
        description=f"Félicitations {interaction.user.mention} !",
        color=discord.Color.gold(),
        timestamp=date_obj
    )
    embed.add_field(name="Pokémon", value=pokemon, inline=True)
    embed.add_field(name="Méthode", value=methode, inline=True)
    embed.add_field(name="Odds", value=odds, inline=True)
    embed.add_field(name="Date", value=date_formatted, inline=True)
    embed.add_field(name="Points obtenus", value=f"{points} ⭐", inline=True)
    embed.set_footer(text="ShinyBot - Merci à toi bgette/bg !")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="shiny_remove",
    description="Supprimer le dernier shiny ajouté par un membre (Admin uniquement).",
    guild=discord.Object(id=GUILD_ID)
)
@app_commands.describe(
    member="Membre dont on veut annuler le dernier shiny"
)
async def shiny_remove(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Vous devez être administrateur pour utiliser cette commande.", ephemeral=True)
        return

    user_id = str(member.id)
    cursor.execute("SELECT rowid FROM shiny WHERE user_id = ? ORDER BY rowid DESC LIMIT 1", (user_id,))
    result = cursor.fetchone()
    if not result:
        await interaction.response.send_message(f"⚠️ Aucun shiny trouvé pour {member.mention}.", ephemeral=True)
        return

    rowid_to_delete = result[0]
    cursor.execute("DELETE FROM shiny WHERE rowid = ?", (rowid_to_delete,))
    conn.commit()
    await interaction.response.send_message(f"✅ Le dernier shiny de {member.mention} a bien été supprimé.")

@bot.tree.command(
    name="classement",
    description="Afficher le classement shiny",
    guild=discord.Object(id=GUILD_ID)
)
async def classement(interaction: discord.Interaction):
    ladder_list = get_ladder()
    if not ladder_list:
        await interaction.response.send_message("Le ladder est vide.")
        return

    guild = bot.get_guild(GUILD_ID)
    if guild is None:
        await interaction.response.send_message("Erreur: serveur non trouvé.")
        return

    embed = discord.Embed(
        title="🏆 Classement Shiny 🏆",
        description="Voici le classement des meilleurs shiny hunters !",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )

    def get_rank_role(position: int) -> str:
        if position == 1:
            return "Shiny Hunter 1"
        elif 2 <= position <= 5:
            return "Shiny Master"
        elif 6 <= position <= 15:
            return "Shiny de Platine"
        elif 16 <= position <= 25:
            return "Shiny d'Or"
        elif 26 <= position <= 35:
            return "Shiny d'Argent"
        else:
            return "Shiny Novice"

    for position, (user_id, total_points) in enumerate(ladder_list, start=1):
        member = guild.get_member(int(user_id))
        if member:
            role_name = get_rank_role(position)
            embed.add_field(
                name=f"#{position} - {member.display_name}",
                value=f"Rank: **{role_name}** | Points : **{total_points}**",
                inline=False
            )

    embed.set_footer(text="ShinyBot - Continuer à Shasser les shiny !")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="shiny_points", description="Affiche le barème des points shiny", guild=discord.Object(id=GUILD_ID))
async def shiny_points(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📊 Barème des points Shiny",
        color=discord.Color.gold()
    )
    embed.add_field(name="Full Odds 1/8192", value="50 points", inline=False)
    embed.add_field(name="Full Odds Herbes double 1/8192", value="25 points", inline=False)
    embed.add_field(name="Full Odds 1/4096", value="25 points", inline=False)
    embed.add_field(name="Full Odds Herbes double 1/4096", value="12 points", inline=False)
    embed.add_field(name="Starter HG/SS & Casino ALL GEN 1/8192", value="15 points", inline=False)
    embed.add_field(name="Charme Chroma (1/2370) 5G", value="15 points", inline=False)
    embed.add_field(name="Charme Chroma (1/1365)", value="10 points", inline=False)
    embed.add_field(name="Masuda 5G", value="5 points", inline=False)
    embed.add_field(name="Hordes sans Charme Chroma/Pokéradar Full Odds", value="5 points", inline=False)
    embed.add_field(name="Hordes Charme Chroma", value="3 points", inline=False)
    embed.add_field(name="Méthode (PR/Péche à la chaîne/SOS/Navidex etc...)", value="2 points", inline=False)
    embed.add_field(name="Légendes Arceus", value="1 point", inline=False)
    embed.add_field(name="Pokémon Violet Écarlate Full Odds", value="4 points", inline=False)
    embed.add_field(name="Charme Chroma Violet Écarlate", value="2 points", inline=False)
    embed.add_field(name="Sandwich Shiny/Apparition massive", value="1 point", inline=False)
    embed.set_footer(text="*Si l’odds est 'Switch 2', les points sont divisés par 2.*")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(
    name="reset_saison",
    description="Réinitialiser tous les points shiny (Admin uniquement).",
    guild=discord.Object(id=GUILD_ID)
)
async def reset_saison(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Vous devez être administrateur pour utiliser cette commande.", ephemeral=True)
        return

    cursor.execute("DELETE FROM shiny")
    conn.commit()

    await interaction.response.send_message("✅ Tous les points shiny ont été réinitialisés.")

# -- Début ajout Flask Keep Alive --

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()

# -- Fin ajout Flask Keep Alive --

token = os.environ['TOKEN']

keep_alive()
bot.run(token)
