import discord
from discord.ext import commands
import random
import os
import csv

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from Render's environment variables

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)  # Add a dummy prefix

# Load degrees of success from CSV
def load_thresholds():
    thresholds = []
    success_labels = []
    
    with open("thresholds.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0].isdigit():  # Only append valid numeric thresholds
                thresholds.append(float(row[0]) / 100)  # Convert % to decimal
            success_labels.append(row[1])  # Store success labels
    
    return thresholds, success_labels

THRESHOLDS, SUCCESS_LABELS = load_thresholds()  # Load at startup



@bot.tree.command(name="alea")
async def alea(interaction: discord.Interaction, tv: int, ld: int = 0, verbose: bool = False):
    """Effettua un tiro ALEA con risposta differita per evitare timeout"""

    # Acknowledge the interaction immediately to prevent timeout issues
    await interaction.response.defer()

    # Perform the dice roll calculations
    result = alea_roll(tv, ld)

    # Compute Success Boundaries (Highest number of each category)
    boundaries = [round(tv * threshold) for threshold in THRESHOLDS]

    # Identify where the result falls
    position = next((i for i, bound in enumerate(boundaries) if result["Tiro Manovra (con LD)"] <= bound), len(boundaries))

    # Get the three closest degrees of success
    min_index = max(position - 1, 0)
    max_index = min(position + 1, len(boundaries) - 1)

    selected_labels = [
        SUCCESS_LABELS[min_index],  # Left
        SUCCESS_LABELS[position],   # Middle (bold)
        SUCCESS_LABELS[max_index]   # Right
    ]

    selected_ranges = [
        f"{boundaries[min_index-1]+1}-{boundaries[min_index]}",  
        f"{boundaries[position-1]+1}-{boundaries[position]}",  
        f"{boundaries[max_index-1]+1}-{boundaries[max_index]}"  
    ]

    # Handle "Tiro Aperto" (Exploding Rolls)
    tiro_aperto_text = ""
    if result["Tiro Aperto"]:
        tiro_aperto_text = f"\n🌀 **Tiro Aperto!** Il primo tiro (`{result['Primo Tiro']}`) ha attivato un reroll → `{result['Reroll']}`."

    # Format table in a Discord embed for better readability
    table = "```\n"
    table += f" {selected_labels[0]:<6} | {selected_labels[1]:<6} | {selected_labels[2]:<6} \n"
    table += "------|------|------\n"
    table += f" {selected_ranges[0]:<6} | \033[1m{selected_ranges[1]:<6}\033[0m | {selected_ranges[2]:<6} \n"  # Bold middle column
    table += "```"

    # Emphasized Result Formatting
    result_line = f"## 🎯 __RISULTATO:__ `{result['Risultato']}` 🎯"

    # Create an embed message
    embed = discord.Embed(
        title="🎲 **Tiro ALEA**",
        description=(
            f"🕹️ **Tiro 1d100:** `{result['Tiro 1d100']}`\n"
            f"📊 **Tiro Manovra (con LD):** `{result['Tiro Manovra (con LD)']}`\n"
            f"📏 **Valore Soglia (VS):** `{result['Valore Soglia (VS)']}`\n"
            f"🎯 **Livello Difficoltà (LD):** `{result['Livello Difficoltà (LD)']}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"{result_line}\n"
            "━━━━━━━━━━━━━━━"
            f"{tiro_aperto_text}"
        ),
        color=discord.Color.gold()
    )

    # Add the formatted table inside the embed
    embed.add_field(name="Soglie di Successo", value=table, inline=False)

    # Optional: Add an ALEA-themed thumbnail or Star Trek image
    embed.set_thumbnail(url="https://your-image-url-here.png")  # Change to a relevant image

    # Show verbose calculation if requested
    if verbose:
        calc_text = f"🔍 **Calcoli Dettagliati**:\n" \
                    f"- **Tiro 1d100:** `{result['Tiro 1d100']}`\n" \
                    f"- **Modificatore LD:** `{ld}`\n" \
                    f"- **Tiro Manovra:** `{result['Tiro Manovra (con LD)']}`\n" \
                    f"- **Confini di Successo:** `{', '.join(map(str, boundaries))}`"
        embed.add_field(name="📜 Modalità Verbose", value=calc_text, inline=False)

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
    tiro_aperto = False
    reroll_value = None

    # Handle "Tiro Aperto" logic
    if first_roll in range(1, 6):  
        reroll_value = random.randint(1, 100)
        final_roll -= reroll_value
        tiro_aperto = True
    elif first_roll in range(96, 101):  
        reroll_value = random.randint(1, 100)
        final_roll += reroll_value
        tiro_aperto = True

    final_roll += ld

    ratio = (final_roll / tv) * 100 if tv > 0 else float('inf')
    result = SUCCESS_LABELS[next((i for i, bound in enumerate(THRESHOLDS) if final_roll <= bound), len(SUCCESS_LABELS) - 1)]

    return {
        "Primo Tiro": first_roll,
        "Reroll": reroll_value,
        "Tiro Aperto": tiro_aperto,
        "Tiro 1d100": first_roll,
        "Tiro Manovra (con LD)": final_roll,
        "Valore Soglia (VS)": tv,
        "Livello Difficoltà (LD)": ld,
        "Risultato": result
    }


bot.run(TOKEN)
