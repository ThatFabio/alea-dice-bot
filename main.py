import discord
from discord.ext import commands
import random
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from Render's environment variables

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)  # Add a dummy prefix


@bot.tree.command(name="alea")
async def alea(interaction: discord.Interaction, tv: int, ld: int):
    """Effettua un tiro ALEA con risposta differita per evitare timeout"""

    # Acknowledge the interaction immediately to prevent timeout issues
    await interaction.response.defer()

    # Perform the dice roll calculations
    result = alea_roll(tv, ld)

    # Success/Failure Thresholds with 2-digit padding (01 to 00)
    thresholds = [
        f"{round(tv * 0.10):02}",  # S4 (10%)
        f"{round(tv * 0.50):02}",  # S3 (50%)
        f"{round(tv * 0.90):02}",  # S2 (90%)
        f"{round(tv * 1.00):02}",  # S1 (100%)
        f"{round(tv * 1.10):02}",  # F1 (110%)
        f"{round(tv * 1.50):02}",  # F2 (150%)
        f"{round(tv * 1.90):02}",  # F3 (190%)
        f"{round(tv * 2.00):02}"   # F4 (200%)
    ]

    # Success/Failure Labels
    labels = ["S4", "S3", "S2", "S1", "F1", "F2", "F3", "F4"]

    # Determine where the final roll fits (column 3)
    checkmarks = [" " for _ in range(8)]  # Default to empty spaces
    for i in range(len(thresholds)):
        if result["Tiro Manovra (con LD)"] <= int(thresholds[i]):
            checkmarks[i] = "✅"  # Mark the correct column
            break

    # Define fixed-width columns for perfect spacing
    col_width = 8  # Each column will be 8 characters wide

    # Format each row using fixed-width alignment
    header_row = "".join(f"{label:^{col_width}}" for label in labels)
    value_row = "".join(f"{value:^{col_width}}" for value in thresholds)
    checkmark_row = "".join(f"{mark:^{col_width}}" for mark in checkmarks)

    # Format the table using a Discord code block (monospace)
    table = f"```\n{header_row}\n{value_row}\n{checkmark_row}\n```"

    # Emphasized Result Formatting
    result_line = f"## 🎯 __RISULTATO:__ `{result['Risultato']}` 🎯"

    # Create an embed message
    embed = discord.Embed(
        title="🎲 **Tiro ALEA**",
        description=f"**Tiro 1d100:** `{result['Tiro 1d100']}`\n"
                    f"**Tiro Manovra (con LD):** `{result['Tiro Manovra (con LD)']}`\n"
                    f"**Valore Soglia (VS):** `{result['Valore Soglia (VS)']}`\n"
                    f"**Livello Difficoltà (LD):** `{result['Livello Difficoltà (LD)']}`\n"
                    "━━━━━━━━━━━━━━━\n"
                    f"{result_line}\n"
                    "━━━━━━━━━━━━━━━",
        color=discord.Color.gold()
    )

    # Add the transposed table inside the embed
    embed.add_field(name="Gradi di Successo", value=table, inline=False)

    # Optional: Add an ALEA-themed thumbnail or Star Trek image
    embed.set_thumbnail(url="https://your-image-url-here.png")  # Change to a relevant image

    # Send the final response (after deferring)
    await interaction.followup.send(embed=embed)


@bot.event
async def on_ready():
    if not hasattr(bot, "synced"):
        try:
            synced = await bot.tree.sync()  # Sync slash commands
            print(f"Synced {len(synced)} commands")
            bot.synced = True  # Prevents multiple sync attempts
        except Exception as e:
            print(f"Errore nella sincronizzazione dei comandi: {e}")


def alea_roll(tv, ld, lucky_number=None):
    first_roll = random.randint(1, 100)
    final_roll = first_roll

    if first_roll in range(1, 6):  
        reroll = random.randint(1, 100)
        final_roll -= reroll
    elif first_roll in range(96, 101):  
        reroll = random.randint(1, 100)
        final_roll += reroll

    final_roll += ld

    ratio = (final_roll / tv) * 100 if tv > 0 else float('inf')
    result = ("Successo Assoluto" if ratio <= 10 else
              "Successo Pieno" if ratio <= 50 else
              "Successo Parziale" if ratio <= 90 else
              "Successo Minimo" if ratio <= 100 else
              "Fallimento Minimo" if ratio <= 110 else
              "Fallimento Parziale" if ratio <= 150 else
              "Fallimento Pieno" if ratio <= 190 else
              "Fallimento Critico")

    return {
        "Tiro 1d100": first_roll,
        "Tiro Manovra (con LD)": final_roll,
        "Valore Soglia (VS)": tv,
        "Livello Difficoltà (LD)": ld,
        "Risultato": result
    }


bot.run(TOKEN)
