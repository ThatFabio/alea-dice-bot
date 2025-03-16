import os
import threading
import random
import discord
from discord.ext import commands
import csv
from flask import Flask

# === Flask Keep-Alive Server ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    port = int(os.environ.get('PORT', 8080))  # Render requires a PORT
    app.run(host='0.0.0.0', port=port)

# === Load Environment Variables ===
TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from Render's environment variables

# === Load Degrees of Success from CSV ===
def load_thresholds():
    thresholds = []
    success_labels = []
    success_acronyms = []
    
    with open("thresholds.csv", newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if row[0].isdigit():  # Only append valid numeric thresholds
                thresholds.append(float(row[0]) / 100)  # Convert % to decimal
            success_labels.append(row[1])  # Full label
            success_acronyms.append(row[2])  # Acronym
    
    return thresholds, success_labels, success_acronyms

THRESHOLDS, SUCCESS_LABELS, SUCCESS_ACRONYMS = load_thresholds()  # Load at startup

# === Initialize Discord Bot ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="alea")
async def alea(interaction: discord.Interaction, tv: int, ld: int = 0, verbose: bool = True):
    """Effettua un tiro ALEA con risposta differita per evitare timeout"""

    # Acknowledge the interaction immediately to prevent timeout issues
    await interaction.response.defer()

    # Perform the dice roll calculations
    result = alea_roll(tv, ld)

    # Compute Success Boundaries (Highest number of each category)
    boundaries = [round(tv * threshold) for threshold in THRESHOLDS]

    # Identify where the result falls
    position = next((i for i, bound in enumerate(boundaries) if result["Tiro Manovra (con LD)"] <= bound), len(boundaries))

    # Ensure proper range formatting
    def format_range(low, high):
        return f"[{low} - {high}]"  # No leading zeros

    # Get the range of the achieved success level
    low = boundaries[position-1] + 1 if position > 0 else 1
    high = boundaries[position]
    range_text = format_range(low, high)

    # Handle "Tiro Aperto" (Exploding Rolls)
    tiro_aperto_text = ""
    if result["Tiro Aperto"]:
        tiro_aperto_text = f"\n**Tiro Aperto!** Il primo tiro (`{result['Primo Tiro']}`) ha attivato un reroll → `{result['Reroll']}`."

    # Format output based on verbosity
    if not verbose:
        summary = f"## {SUCCESS_LABELS[position]} {range_text}"
    else:
        summary = ""
        for i in range(len(boundaries)):
            low = boundaries[i-1] + 1 if i > 0 else 1
            high = boundaries[i]
            range_text = format_range(low, high)
            checkmark = " ✅" if i == position else ""
            summary += f"**{SUCCESS_LABELS[i]}** {range_text}{checkmark}\n"

    # Create an embed message
    embed = discord.Embed(
        title=f"**Tiro 1d100: {result['Tiro 1d100']}**",
        description=(
            f"**Tiro Manovra (con LD):** `{result['Tiro Manovra (con LD)']}`\n"
            f"**Valore Soglia (VS):** `{result['Valore Soglia (VS)']}`\n"
            f"**Livello Difficoltà (LD):** `{result['Livello Difficoltà (LD)']}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"{summary}\n"
            "━━━━━━━━━━━━━━━"
            f"{tiro_aperto_text}"
        ),
        color=discord.Color.blue()
    )

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

# === Run Flask Keep-Alive Server in a Separate Thread ===
server_thread = threading.Thread(target=run_server)
server_thread.start()

# === Start Discord Bot ===
bot.run(TOKEN)
