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

# === Format Success Levels with Dynamic Intervals ===
def format_success_levels():
    """
    Genera la sezione Gradi di Successo dal file thresholds.csv con intervalli dinamici.
    Divide i livelli in Successi (S) e Fallimenti (F) con VS (100%) come spartiacque.
    """
    if not THRESHOLDS or len(THRESHOLDS) == 0:
        return "Nessun livello di successo configurato."
    
    # Separa successi (threshold < 1.0) e fallimenti (threshold >= 1.0)
    successi = [(THRESHOLDS[i], SUCCESS_LABELS[i]) for i in range(len(THRESHOLDS)) if THRESHOLDS[i] < 1.0]
    fallimenti = [(THRESHOLDS[i], SUCCESS_LABELS[i]) for i in range(len(THRESHOLDS)) if THRESHOLDS[i] >= 1.0]
    
    lines = []
    lines.append(f"La configurazione attuale utilizza {len(THRESHOLDS)} livelli di successo:\n")
    
    # Aggiungi i successi (da S_n a S1, da più raro a meno raro)
    for idx, (threshold, label) in enumerate(successi):
        level_num = len(successi) - idx  # S_n, S_(n-1), ..., S1
        emoji = "🟢"
        
        if idx == 0:
            # Primo successo (più raro): da 0% al primo threshold
            interval = f"[meno di {threshold*100:.0f}%]"
        else:
            # Successi intermedi: tra due threshold
            prev_threshold = successi[idx-1][0]
            interval = f"[{prev_threshold*100:.0f}% - {threshold*100:.0f}%]"
        
        lines.append(f"{emoji} S{level_num} {interval} {label}")
    
    # Aggiungi i fallimenti (da F1 a F_m, da meno raro a più raro)
    for idx, (threshold, label) in enumerate(fallimenti):
        level_num = idx + 1  # F1, F2, F3, ...
        
        # Emoji: rossa per fallimenti, nera per fallimento critico (ultimo)
        if idx == len(fallimenti) - 1:
            emoji = "⚫"
        else:
            emoji = "🔴"
        
        if idx == 0:
            # Primo fallimento: dal confine (ultimo successo o 0%) al primo fallimento
            if len(successi) > 0:
                prev_threshold = successi[-1][0]
                interval = f"[{prev_threshold*100:.0f}% - {threshold*100:.0f}%]"
            else:
                interval = f"[0% - {threshold*100:.0f}%]"
        elif idx == len(fallimenti) - 1:
            # Ultimo fallimento (critico): oltre il precedente
            prev_threshold = fallimenti[idx-1][0]
            interval = f"[più di {prev_threshold*100:.0f}%]"
        else:
            # Fallimenti intermedi: tra due threshold
            prev_threshold = fallimenti[idx-1][0]
            interval = f"[{prev_threshold*100:.0f}% - {threshold*100:.0f}%]"
        
        lines.append(f"{emoji} F{level_num} {interval} {label}")
    
    return "\n".join(lines)

# === Initialize Discord Bot ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="alea", description="Effettua un tiro ALEA")
async def alea(interaction: discord.Interaction, vs: int, ld: int = 0, verbose: bool = False):
    """Effettua un tiro ALEA con risposta differita per evitare timeout"""

    # Acknowledge the interaction immediately to prevent timeout issues
    await interaction.response.defer()

    # Perform the dice roll calculations
    result = dice_roll(vs, ld)

    # Compute Success Boundaries (Highest number of each category)
    boundaries = [round(vs * threshold) for threshold in THRESHOLDS]

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
            f"**VS (Valore Soglia):** `{result['Valore Soglia (VS)']}`\n"
            f"**LD (Livello Difficoltà):** `{result['Livello Difficoltà (LD)']}`\n"
            "━━━━━━━━━━━━━━━\n"
            f"{summary}\n"
            "━━━━━━━━━━━━━━━"
            f"{tiro_aperto_text}"
        ),
        color=discord.Color.blue()
    )

    # Send the final response (after deferring)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="alea-help", description="Mostra aiuto su come usare il comando /alea")
async def alea_help(interaction: discord.Interaction):
    """Mostra aiuto su come usare il comando /alea"""
    
    embed = discord.Embed(
        title="📖 Guida al Comando /alea",
        description="Come usare il sistema di tiri ALEA",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="Utilizzo Base",
        value="`/alea vs:80`\n\nEsegue un tiro 1d100 contro un Valore Soglia (VS) di 80.",
        inline=False
    )
    
    embed.add_field(
        name="Parametri",
        value="**vs** (Valore Soglia): Valore Soglia richiesto (0-999+) - *Obbligatorio*\n"
              "**ld** (Livello Difficoltà): Modificatore di difficoltà (-60 a +60) - *Opzionale, default: 0*\n"
              "**Verbose**: Mostra tutti i Gradi di Successo o solo il risultato (true/false) - *Opzionale, default: false*",
        inline=False
    )
    
    embed.add_field(
        name="Esempi",
        value="`/alea vs:85 ld:10` - Tiro con VS 85 e +10 di difficoltà\n"
              "`/alea vs:50 Verbose:true` - Mostra tutti i Gradi di Successo\n"
              "`/alea vs:100 ld:-5` - Tiro facilitato di 5 punti",
        inline=False
    )
    
    embed.add_field(
        name="Gradi di Successo",
        value=format_success_levels(),
        inline=False
    )
    
    embed.add_field(
        name="Tiro Aperto",
        value="Se il 1d100 risulta 1-5 (critico di successo) o 96-100 (critico di fallimento),\n"
              "il bot esegue automaticamente un reroll e lo combina con il primo risultato!",
        inline=False
    )
    
    embed.set_footer(text="Sistema ALEA GdR - Tira i dadi con stile!")
    
    await interaction.response.send_message(embed=embed)

@bot.event
async def on_ready():
    if not hasattr(bot, "synced"):
        try:
            synced = await bot.tree.sync()  # Sync slash commands
            print(f"Synced {len(synced)} commands")
            bot.synced = True  # Prevents multiple sync attempts
        except Exception as e:
            print(f"Errore nella sincronizzazione dei comandi: {e}")

def dice_roll(vs, ld, lucky_number=None):
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

    ratio = (final_roll / vs) * 100 if vs > 0 else float('inf')
    result = SUCCESS_LABELS[next((i for i, bound in enumerate(THRESHOLDS) if final_roll <= bound), len(SUCCESS_LABELS) - 1)]

    return {
        "Primo Tiro": first_roll,
        "Reroll": reroll_value,
        "Tiro Aperto": tiro_aperto,
        "Tiro 1d100": first_roll,
        "Tiro Manovra (con LD)": final_roll,
        "Valore Soglia (VS)": vs,
        "Livello Difficoltà (LD)": ld,
        "Risultato": result
    }

# === Run Flask Keep-Alive Server in a Separate Thread ===
server_thread = threading.Thread(target=run_server)
server_thread.start()

# === Start Discord Bot ===
bot.run(TOKEN)
