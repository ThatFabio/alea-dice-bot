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
            # Skip empty rows or rows with insufficient columns
            if not row or len(row) < 3:
                continue

            first = row[0].strip()
            # Try parsing the threshold as an integer (allow floats too)
            try:
                val = int(first)
            except ValueError:
                try:
                    val = int(float(first))
                except Exception:
                    continue

            # Normalize and cap sentinel: do not accept negative values
            if val < 0:
                continue

            if val > 999:
                val = 999

            thresholds.append(float(val) / 100)
            success_labels.append(row[1].strip())
            success_acronyms.append(row[2].strip())

            # If sentinel 999 found, stop parsing further rows
            if val == 999:
                break

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
    
    # Separa successi (threshold <= 1.0, incluso il confine VS=100%) e fallimenti (threshold > 1.0)
    successi = [(THRESHOLDS[i], SUCCESS_LABELS[i]) for i in range(len(THRESHOLDS)) if THRESHOLDS[i] <= 1.0]
    fallimenti = [(THRESHOLDS[i], SUCCESS_LABELS[i]) for i in range(len(THRESHOLDS)) if THRESHOLDS[i] > 1.0]
    
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


def dice_roll(vs, ld, malus_stato=0, compute_label=True):
    """
    Perform a classic ALEA 1d100 roll applying LD (added to the roll) and state malus.
    Handles "Tiro Aperto" (exploding) on 1-5 (subtract reroll) and 96-100 (add reroll).
    Returns a dict with keys used by the /alea command.
    """
    # Primo tiro 1-100
    primo_tiro = random.randint(1, 100)
    final_roll = primo_tiro

    tiro_aperto = False
    reroll_value = None

    # Handle "Tiro Aperto" (exploding rolls)
    if 1 <= primo_tiro <= 5:
        reroll_value = random.randint(1, 100)
        final_roll -= reroll_value
        tiro_aperto = True
    elif 96 <= primo_tiro <= 100:
        reroll_value = random.randint(1, 100)
        final_roll += reroll_value
        tiro_aperto = True

    # Apply LD (classic ALEA uses LD added to the roll on the left)
    final_roll += ld

    # Apply malus from status (added to the roll)
    try:
        final_roll += int(malus_stato)
    except Exception:
        pass

    # Ensure integer
    final_roll = int(final_roll)

    result_label = None
    if compute_label:
        # Compute human-readable result label (safe fallback to last label)
        try:
            idx = next((i for i, bound in enumerate(THRESHOLDS) if final_roll <= bound), len(SUCCESS_LABELS) - 1)
            result_label = SUCCESS_LABELS[idx]
        except Exception:
            result_label = "Risultato sconosciuto"

    return {
        "Primo Tiro": primo_tiro,
        "Reroll": reroll_value,
        "Tiro Aperto": tiro_aperto,
        "Tiro 1d100": primo_tiro,
        "Tiro Manovra (con LD)": final_roll,
        "Valore Soglia (VS)": vs,
        "Livello Difficoltà (LD)": ld,
        "Risultato": result_label
    }

# === Initialize Discord Bot ===
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="alea", description="Effettua un tiro ALEA con parametri completi del sistema MISO")
async def alea(interaction: discord.Interaction, vs: int = 0, ld: int = 0, verbose: bool = False,
              car: int = 0, abi: int = 0, spec: int = 0, lf: int = 0, la: int = 0, ls: int = 0):
    """Effettua un tiro ALEA con parametri opzionali del sistema MISO"""

    # Acknowledge the interaction immediately to prevent timeout issues
    await interaction.response.defer()
    
    # Converti SPEC da {0, 1, 2} a {0, 20, 30}
    if spec not in [0, 1, 2]:
        await interaction.followup.send("❌ SPEC deve essere 0, 1 o 2 (non 20 o 30)", ephemeral=True)
        return
    spec_value = {0: 0, 1: 20, 2: 30}[spec]
    
    # Allow shorthand call like "/alea 50" — try to extract first raw option value if vs is still 0
    if vs == 0:
        try:
            data = getattr(interaction, 'data', None)
            if data:
                opts = data.get('options', [])
                if opts:
                    # find first option with a concrete value
                    for o in opts:
                        if 'value' in o:
                            try:
                                maybe_vs = int(o['value'])
                                if maybe_vs >= 0:
                                    vs = maybe_vs
                                    break
                            except Exception:
                                # not an integer, ignore
                                pass
        except Exception:
            pass

    # Se VS non è fornito direttamente, calcola da CAR+ABI+SPEC
    if vs == 0 and (car > 0 or abi > 0 or spec > 0):
        vs = car + abi + spec_value
        if vs == 0:
            await interaction.followup.send("❌ Devi fornire VS direttamente o almeno uno tra CAR, ABI, SPEC", ephemeral=True)
            return
    elif vs == 0:
        await interaction.followup.send("❌ Devi fornire il Valore Soglia (VS) o i parametri CAR/ABI/SPEC", ephemeral=True)
        return
    
    # Calcola malus da stato
    malus_lf = 0 if lf <= 3 else (20 if lf <= 5 else (40 if lf <= 7 else (60 if lf <= 9 else float('inf'))))
    malus_la = 0 if la == 0 else (20 if la == 1 else (40 if la == 2 else (60 if la == 3 else float('inf'))))
    malus_ls = 0 if ls == 0 else (20 if ls == 1 else (40 if ls == 2 else (60 if ls == 3 else float('inf'))))
    malus_stato = malus_lf + malus_la + malus_ls

    # If the user invoked /alea with no parameters at all, just roll and return the final die value
    no_params = (vs == 0 and car == 0 and abi == 0 and spec == 0 and lf == 0 and la == 0 and ls == 0 and ld == 0)
    if no_params:
        minimal = dice_roll(vs, ld, malus_stato, compute_label=False)
        tiro_aperto_text = ""
        if minimal.get("Tiro Aperto"):
            tiro_aperto_text = f"\n**Tiro Aperto!** Il primo tiro (`{minimal['Primo Tiro']}`) ha attivato un reroll → `{minimal['Reroll']}`."

        embed = discord.Embed(
            title=f"**Tiro 1d100: {minimal['Tiro 1d100']}**",
            description=(
                f"**Tiro Manovra (con LD+Stati):** `{minimal['Tiro Manovra (con LD)']}`\n"
                f"━━━━━━━━━━━━━━━\n"
                f"(Risultato grezzo, nessun confronto con Gradi di Successo){tiro_aperto_text}"
            ),
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed)
        return

    # Perform the dice roll calculations (normal flow)
    result = dice_roll(vs, ld, malus_stato)

    # Compute Success Boundaries (exclude sentinel last threshold from numeric calcs)
    if len(THRESHOLDS) > 1:
        numeric_thresholds = THRESHOLDS[:-1]
    else:
        numeric_thresholds = THRESHOLDS

    boundaries = [round(vs * t) for t in numeric_thresholds]

    # Determine label index: first boundary <= final roll -> corresponding label index
    final_value = result["Tiro Manovra (con LD)"]
    label_index = None
    for i, b in enumerate(boundaries):
        if final_value <= b:
            label_index = i
            break
    if label_index is None:
        # above all numeric boundaries -> Fallimento Critico (last label)
        label_index = len(SUCCESS_LABELS) - 1

    # Ensure proper range formatting with open extremes
    def format_range(label_i):
        if len(boundaries) == 0:
            return f"[1 - {vs}]"
        # First label: everything below first boundary (open lower)
        if label_i == 0:
            return f"[meno di {boundaries[0]}]"
        # Last label (Fallimento Critico): anything above the last numeric boundary
        if label_i == len(SUCCESS_LABELS) - 1:
            prev = boundaries[-1]
            return f"[più di {prev}]"
        # Middle labels: closed interval
        low = boundaries[label_i-1] + 1
        high = boundaries[label_i]
        return f"[{low} - {high}]"

    range_text = format_range(label_index)

    # Handle "Tiro Aperto" (Exploding Rolls)
    tiro_aperto_text = ""
    if result["Tiro Aperto"]:
        tiro_aperto_text = f"\n**Tiro Aperto!** Il primo tiro (`{result['Primo Tiro']}`) ha attivato un reroll → `{result['Reroll']}`."

    # Format output based on verbosity
    if not verbose:
        summary = f"## {SUCCESS_LABELS[label_index]} {range_text}"
    else:
        summary = ""
        # iterate all labels, including final Fallimento Critico
        for i in range(len(SUCCESS_LABELS)):
            rtext = format_range(i)
            checkmark = " ✅" if i == label_index else ""
            summary += f"**{SUCCESS_LABELS[i]}** {rtext}{checkmark}\n"

    # Create an embed message
    # Crea stringa parametri aggiuntivi se forniti
    param_extra = ""
    if car > 0 or abi > 0 or spec > 0:
        param_extra += f"**CAR (Caratteristica):** `{car}` | **ABI (Abilità):** `{abi}` | **SPEC:** `{spec}` (={spec_value})\n"
    if lf > 0 or la > 0 or ls > 0:
        param_extra += f"**LF (Ferite):** `{lf}` | **LA (Affaticamento):** `{la}` | **LS (Stordimento):** `{ls}`\n"
    
    embed = discord.Embed(
        title=f"**Tiro 1d100: {result['Tiro 1d100']}**",
        description=(
            f"**Tiro Manovra (con LD+Stati):** `{result['Tiro Manovra (con LD)']}`\n"
            f"**VS (Valore Soglia):** `{result['Valore Soglia (VS)']}`\n"
            f"**LD (Livello Difficoltà):** `{result['Livello Difficoltà (LD)']}`\n"
            f"{param_extra}"
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
        name="Parametri Base",
        value="**vs** (Valore Soglia): Valore Soglia diretto (0-999+) - *Opzionale se forniti CAR/ABI/SPEC*\n"
              "**ld** (Livello Difficoltà): Modificatore di difficoltà (-60 a +60) - *Opzionale, default: 0*\n"
              "**verbose**: Mostra tutti i Gradi di Successo o solo il risultato (true/false) - *Opzionale, default: false*",
        inline=False
    )
    
    embed.add_field(
        name="Parametri MISO Avanzati (Opzionali)",
        value="**car** (Caratteristica): Valore caratteristica (0-50+)\n"
              "**abi** (Abilità): Valore abilità (0-100+)\n"
              "**spec** (Specializzazione): Livello specializzazione {0=nessuna, 1=+20, 2=+30}\n"
              "**lf** (Livello Ferite): Livello ferite (0-10)\n"
              "**la** (Livello Affaticamento): Livello affaticamento (0-4)\n"
              "**ls** (Livello Stordimento): Livello stordimento (0-4)\n\n"
              "*Se forniti CAR/ABI/SPEC e VS=0, VS viene calcolato: VS = CAR + ABI + SPEC*",
        inline=False
    )
    
    embed.add_field(
        name="Esempi",
        value="`/alea vs:85 ld:10` - Tiro con VS 85 e +10 di difficoltà\n"
              "`/alea car:25 abi:45 spec:2` - Tiro calcolato (25+45+30=100)\n"
              "`/alea vs:50 lf:4 la:1` - Con ferita leggera + affaticamento\n"
              "`/alea vs:100 verbose:true` - Mostra tutti i Gradi di Successo",
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

# === ALEA99 System ===
def dice_roll_alea99(n, vs, ld):
    """
    Sistema ALEA99: tira N d10, prende i 2 più bassi, calcola risultato come numero 2-cifre.
    VS_effettivo = VS + LD
    
    Gradi di Successo:
    - Successo Assoluto (SA): cifre identiche e <= VS_effettivo
    - Successo Pieno (SP): cifre diverse e <= VS_effettivo
    - Fallimento Pieno (FP): cifre diverse e > VS_effettivo
    - Fallimento Critico (FC): cifre identiche e > VS_effettivo
    """
    # Tira N d10 [0..9]
    rolls = [random.randint(0, 9) for _ in range(n)]
    
    # Ordina e prendi i 2 più bassi
    rolls_sorted = sorted(rolls)
    two_lowest = rolls_sorted[:2]
    
    # Forma il numero: primo dado è decina, secondo è unità
    result_value = two_lowest[0] * 10 + two_lowest[1]
    
    # Calcola VS effettivo
    vs_effective = vs + ld
    
    # Determina grado di successo
    has_identical_digits = two_lowest[0] == two_lowest[1]
    is_success = result_value <= vs_effective
    
    if has_identical_digits and is_success:
        success_level = "Successo Assoluto"
        acronym = "SA"
    elif has_identical_digits and not is_success:
        success_level = "Fallimento Critico"
        acronym = "FC"
    elif not has_identical_digits and is_success:
        success_level = "Successo Pieno"
        acronym = "SP"
    else:  # not has_identical_digits and not is_success
        success_level = "Fallimento Pieno"
        acronym = "FP"
    
    return {
        "Numero Dadi": n,
        "Tiri Completi": rolls,
        "Due Più Bassi": two_lowest,
        "Risultato": result_value,
        "VS (Valore Soglia)": vs,
        "LD (Livello Difficoltà)": ld,
        "VS Effettivo": vs_effective,
        "Cifre Identiche": has_identical_digits,
        "Successo Level": success_level,
        "Acronym": acronym
    }

def parse_ld(ld_input):
    """
    Parsa LD da molteplici formati:
    - Numerico: -60, -30, 0, 30, 60
    - Numerico narrativo: -3, -2, -1, 0, 1, 2, 3 (moltiplicato per 20)
    - Narrativo corto: FFF, FF, F, M, D, DD, DDD
    - Narrativo lungo: Banale, Facilissima, Facile, Media, Difficile, Difficilissima, Estrema
    Ritorna valore numerico in [-60, 60]
    """
    ld_input = str(ld_input).strip().upper()
    
    # Mappa narrativa lunga
    narrativa_lunga = {
        "BANALE": -60,
        "FACILISSIMA": -40,
        "FACILE": -20,
        "MEDIA": 0,
        "DIFFICILE": 20,
        "DIFFICILISSIMA": 40,
        "ESTREMA": 60,
    }
    
    # Mappa narrativa corta
    narrativa_corta = {
        "FFF": -60,
        "FF": -40,
        "F": -20,
        "M": 0,
        "D": 20,
        "DD": 40,
        "DDD": 60,
    }
    
    # Prova narrativa lunga
    if ld_input in narrativa_lunga:
        return narrativa_lunga[ld_input]
    
    # Prova narrativa corta
    if ld_input in narrativa_corta:
        return narrativa_corta[ld_input]
    
    # Prova numerico narrativo (-3 a +3)
    try:
        ld_num = int(ld_input)
        if -3 <= ld_num <= 3:
            return ld_num * 20
        elif -60 <= ld_num <= 60 and ld_num % 20 == 0:
            return ld_num
    except ValueError:
        pass
    
    return None

@bot.tree.command(name="alea99", description="Effettua un tiro ALEA99 - Nd10 (best 2)")
async def alea99(interaction: discord.Interaction, 
                 vs: int,
                 spec: int = 0,
                 ld: str = "0",
                 verbose: bool = False):
    """
    Effettua un tiro ALEA99 (Nd10 best 2).
    
    vs (Valore Soglia): 0-99 - *Obbligatorio*
    spec (Specializzazione): 0-3 (converte a N = 2+SPEC → 2d10 a 5d10) - *Opzionale, default: 0*
    ld (Livello Difficoltà): supporta molteplici formati - *Opzionale, default: 0*
        - Numerico: -60, -30, 0, 30, 60
        - Narrativo numerico: -3, -2, -1, 0, 1, 2, 3
        - Narrativo corto: FFF, FF, F, M, D, DD, DDD
        - Narrativo lungo: Banale, Facilissima, Facile, Media, Difficile, Difficilissima, Estrema
    verbose: mostra tutti i Gradi di Successo (default: False)
    """
    
    # Valida VS
    if vs < 0 or vs > 99:
        await interaction.response.send_message("❌ VS deve essere tra 0 e 99", ephemeral=True)
        return
    
    # Valida SPEC
    if spec < 0 or spec > 3:
        await interaction.response.send_message("❌ SPEC deve essere 0, 1, 2 o 3 (N = 2+SPEC, quindi 2-5 dadi)", ephemeral=True)
        return
    
    # Parsa LD
    ld_value = parse_ld(ld)
    if ld_value is None:
        await interaction.response.send_message(
            "❌ LD non riconosciuto. Usa: `-60` a `+60`, oppure `-3` a `+3`, oppure `FFF/FF/F/M/D/DD/DDD`, oppure `Banale/Facilissima/Facile/Media/Difficile/Difficilissima/Estrema`",
            ephemeral=True
        )
        return
    
    # Calcola N da SPEC: N = 2 + SPEC
    n = 2 + spec
    
    await interaction.response.defer()
    
    result = dice_roll_alea99(n, vs, ld_value)
        # Format the rolls display
    rolls_display = " ".join([f"`{d}`" for d in result["Tiri Completi"]])
    two_lowest_display = " ".join([f"**{d}**" for d in result["Due Più Bassi"]])
    
    # Create embed
    embed = discord.Embed(
        title=f"🎲 **{result['Risultato']:02d}** - {result['Acronym']}",
        description=result['Successo Level'],
        color=discord.Color.green() if "Successo" in result['Successo Level'] else discord.Color.red()
    )
    
    embed.add_field(
        name=f"Tiri {n}d10",
        value=f"Tutti i tiri: {rolls_display}\n"
              f"Due più bassi: {two_lowest_display}",
        inline=False
    )
    
    embed.add_field(
        name="Valori",
        value=f"**VS (Valore Soglia):** `{result['VS (Valore Soglia)']}`\n"
              f"**LD (Livello Difficoltà):** `{result['LD (Livello Difficoltà)']}`\n"
              f"**VS Effettivo:** `{result['VS Effettivo']}`\n"
              f"**Cifre identiche:** {'Sì 🟢' if result['Cifre Identiche'] else 'No'}",
        inline=False
    )
    
    if verbose:
        embed.add_field(
            name="Legenda Gradi di Successo",
            value="🟢 **Successo Assoluto (SA):** Cifre identiche e ≤ VS Effettivo\n"
                  "🟡 **Successo Pieno (SP):** Cifre diverse e ≤ VS Effettivo\n"
                  "🔴 **Fallimento Pieno (FP):** Cifre diverse e > VS Effettivo\n"
                  "⚫ **Fallimento Critico (FC):** Cifre identiche e > VS Effettivo",
            inline=False
        )
    
    embed.set_footer(text="Sistema ALEA99 - Tiro Nd10")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="alea99-help", description="Mostra aiuto su come usare il comando /alea99")
async def alea99_help(interaction: discord.Interaction):
    """Mostra aiuto su come usare il comando /alea99"""
    
    embed = discord.Embed(
        title="📖 Guida al Comando /alea99",
        description="Sistema ALEA99: Nd10 con i 2 dadi più bassi",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Utilizzo Base",
        value="`/alea99 vs:50`\n\nTira 2d10 (SPEC=0, default), estrae i 2 più bassi, e confronta con Valore Soglia 50.\n"
              "`/alea99 vs:50 spec:2` - Tira 4d10 (SPEC=2 → N=2+2=4).",
        inline=False
    )
    
    embed.add_field(
        name="Parametri",
        value="**vs** (Valore Soglia): Soglia di confronto (0-99) - *Obbligatorio*\n"
              "**spec** (Specializzazione): Livello specializzazione {0=2d10, 1=3d10, 2=4d10, 3=5d10} - *Opzionale, default: 0*\n"
              "  → Formula: N = 2 + SPEC\n"
              "**ld** (Livello Difficoltà): Modificatore al VS (⚠️ **LD è sulla DESTRA**: VS_effettivo = VS + LD) - *Opzionale, default: 0*\n"
              "**verbose**: Mostra la legenda completa (true/false) - *Opzionale, default: false*",
        inline=False
    )
    
    embed.add_field(
        name="Come Funziona",
        value="1️⃣ Si tirano **N = 2 + SPEC** d10 (valori da 0 a 9)\n"
              "2️⃣ Si **ordinano dal più basso al più alto**\n"
              "3️⃣ Si **prendono solo i 2 più bassi**\n"
              "4️⃣ Si forma un numero a 2 cifre: **[decina][unità]**\n"
              "5️⃣ Si confronta con **VS Effettivo = VS + LD**\n\n"
              "**Esempio:** N=4 → tiri [6, 2, 8, 1] → ordinati [1, 2, 6, 8] → **12** (mai 21)",
        inline=False
    )
    
    embed.add_field(
        name="Gradi di Successo",
        value="🟢 **Successo Assoluto (SA):** Cifre identiche (11, 22, 33...) e ≤ VS Effettivo\n"
              "🟡 **Successo Pieno (SP):** Cifre diverse e ≤ VS Effettivo\n"
              "🔴 **Fallimento Pieno (FP):** Cifre diverse e > VS Effettivo\n"
              "⚫ **Fallimento Critico (FC):** Cifre identiche (11, 22, 33...) e > VS Effettivo",
        inline=False
    )
    
    embed.add_field(
        name="Esempi Pratici",
        value="`/alea99 vs:50` - Tira 2d10 (SPEC=0, default) con VS 50\n"
              "`/alea99 vs:45 spec:1 ld:5` - Tira 3d10 (SPEC=1 → N=3) con VS 45 e LD +5 (VS Effettivo = 50)\n"
              "`/alea99 vs:60 spec:2 verbose:true` - Tira 4d10 (SPEC=2) con VS 60, mostra legenda\n"
              "`/alea99 vs:30 ld:-10` - Tira 2d10 con VS 30 e LD -10 (VS Effettivo = 20)",
        inline=False
    )
    
    embed.add_field(
        name="Tabella Cifre Identiche",
        value="00, 11, 22, 33, 44, 55, 66, 77, 88, 99\n\n"
              "Questi numeri hanno **sempre** conseguenze critiche:\n"
              "✅ Successo se ≤ VS Effettivo (Successo Assoluto)\n"
              "❌ Fallimento se > VS Effettivo (Fallimento Critico)",
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Differenza rispetto a /alea Classico",
        value="**ALEA Classico:** LD è sulla **SINISTRA** della disequazione\n"
              "→ TM = 1d100 + LD, confronto: TM ≤ VS\n\n"
              "**ALEA99:** LD è sulla **DESTRA** della disequazione\n"
              "→ Risultato ≤ VS_effettivo = VS + LD",
        inline=False
    )
    
    embed.set_footer(text="Sistema ALEA99 - Tiro Nd10")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="embed-test", description="Anteprima embed ALEA (opzionale: vs)")
async def embed_test(interaction: discord.Interaction, vs: int = 0, verbose: bool = False):
    """Prototype embed for ALEA results. Use `/embed-test` or `/embed-test vs:50`."""
    await interaction.response.defer()

    # If vs supplied, produce labeled result, otherwise minimal raw roll
    malus_stato = 0
    if vs == 0:
        res = dice_roll(0, 0, malus_stato, compute_label=False)
    else:
        res = dice_roll(vs, 0, malus_stato, compute_label=True)

    # Small responsive visual bar (10 segments) — safe for narrow screens
    def build_bar(value, cap):
        try:
            pct = min(max(value / max(1, cap), 0.0), 1.0)
        except Exception:
            pct = 0.0
        filled = int(round(pct * 10))
        empty = 10 - filled
        return "".join(["🟩" for _ in range(filled)]) + "".join(["⬜" for _ in range(empty)])

    # Prepare compact fields
    if vs == 0:
        title = f"🎲 Tiro 1d100: {res['Tiro 1d100']}"
        description = f"Risultato grezzo — nessun confronto con Gradi di Successo"
    else:
        title = f"🎲 Tiro 1d100: {res['Tiro 1d100']} — {res.get('Risultato', '')}"
        description = f"VS: {vs} | TM: {res['Tiro Manovra (con LD)']}"

    embed = discord.Embed(title=title, description=description, color=discord.Color.blurple())

    # Add compact inline stats to avoid wrapping long lines
    embed.add_field(name="TM (con LD)", value=f"{res['Tiro Manovra (con LD)']}", inline=True)
    embed.add_field(name="VS", value=f"{vs}", inline=True)
    embed.add_field(name="Tiro Aperto", value=("Sì" if res.get("Tiro Aperto") else "No"), inline=True)

    # Visual bar only when VS provided
    if vs > 0:
        bar = build_bar(res['Tiro Manovra (con LD)'], max(1, vs))
        embed.add_field(name="Progresso vs", value=bar, inline=False)

    # Verbose: list ranges from thresholds (short lines)
    if verbose and len(SUCCESS_LABELS) > 0:
        legend = "\n".join([f"{i+1}. {lbl}" for i, lbl in enumerate(SUCCESS_LABELS)])
        embed.add_field(name="Legenda (brevi)", value=legend, inline=False)

    embed.set_footer(text="Anteprima embed ALEA — visuale compatta per tutte le larghezze")

    await interaction.followup.send(embed=embed)


# === Run Flask Keep-Alive Server in a Separate Thread ===
server_thread = threading.Thread(target=run_server)
server_thread.start()

# === Start Discord Bot ===
bot.run(TOKEN)
