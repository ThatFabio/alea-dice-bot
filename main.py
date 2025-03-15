import discord
from discord.ext import commands
import random
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from Render's environment variables

intents = discord.Intents.default()

bot = commands.Bot(command_prefix="!", intents=intents)  # Add a dummy prefix


@bot.tree.command(name="alea")
async def alea(interaction: discord.Interaction, tv: int, ld: int):
    """Rolls an ALEA dice check"""
    result = alea_roll(tv, ld)
    
    # Success/Failure Thresholds
    thresholds = [
        round(tv * 0.10),  # S4 (≤10%)
        round(tv * 0.50),  # S3 (≤50%)
        round(tv * 0.90),  # S2 (≤90%)
        round(tv * 1.00),  # S1 (≤100%)
        round(tv * 1.10),  # F1 (≤110%)
        round(tv * 1.50),  # F2 (≤150%)
        round(tv * 1.90),  # F3 (≤190%)
        round(tv * 2.00)   # F4 (>190%)
    ]
    
    # Success/Failure Labels
    labels = ["S4", "S3", "S2", "S1", "F1", "F2", "F3", "F4"]
    
    # Compute the actual ranges for the second row
    ranges = [
        f"≤{thresholds[0]}",
        f"{thresholds[0]+1}-{thresholds[1]}",
        f"{thresholds[1]+1}-{thresholds[2]}",
        f"{thresholds[2]+1}-{thresholds[3]}",
        f"{thresholds[3]+1}-{thresholds[4]}",
        f"{thresholds[4]+1}-{thresholds[5]}",
        f"{thresholds[5]+1}-{thresholds[6]}",
        f">{thresholds[6]}"
    ]
    
    # Determine where the final roll fits
    checkmarks = ["⬜" for _ in range(8)]  # Default to empty squares
    for i in range(len(thresholds)):
        if result["Final Roll"] <= thresholds[i]:
            checkmarks[i] = "✅"  # Mark the correct column
            break

    # Create an embed message
    embed = discord.Embed(
        title="🎲 ALEA Dice Roll Result",
        description=f"**First Roll:** `{result['First Roll']}`\n"
                    f"**Final Roll (after LD):** `{result['Final Roll']}`\n"
                    f"**Threshold Value (TV):** `{result['Threshold Value (TV)']}`\n"
                    f"**Level of Difficulty (LD):** `{result['Level of Difficulty (LD)']}`\n"
                    f"**Result:** `{result['Result']}`",
        color=discord.Color.blue()
    )

    # Add the formatted table as embed fields
    embed.add_field(name="**Success/Failure Levels**", value=" | ".join(labels), inline=False)
    embed.add_field(name="**Threshold Ranges**", value=" | ".join(ranges), inline=False)
    embed.add_field(name="**Roll Placement**", value=" | ".join(checkmarks), inline=False)

    # Optional: Add an ALEA-themed thumbnail or Star Trek image
    embed.set_thumbnail(url="https://your-image-url-here.png")  # Change to a relevant image

    await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # Sync slash commands
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Error syncing commands: {e}")


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

    if lucky_number and first_roll == lucky_number:
        result = "Critical Success"
    else:
        ratio = (final_roll / tv) * 100 if tv > 0 else float('inf')
        if ratio <= 10:
            result = "Critical Success"
        elif ratio <= 50:
            result = "Full Success"
        elif ratio <= 90:
            result = "Partial Success"
        elif ratio <= 100:
            result = "Minimal Success"
        elif ratio <= 110:
            result = "Minimal Failure"
        elif ratio <= 150:
            result = "Partial Failure"
        elif ratio <= 190:
            result = "Full Failure"
        else:
            result = "Critical Failure"

    return {
        "First Roll": first_roll,
        "Final Roll": final_roll,
        "Threshold Value (TV)": tv,
        "Level of Difficulty (LD)": ld,
        "Result": result
    }

@bot.command(name="alea")
async def alea(ctx, tv: int, ld: int):
    result = alea_roll(tv, ld)
    response = (f"🎲 **ALEA Roll Result** 🎲\n"
                f"First Roll: {result['First Roll']}\n"
                f"Final Roll (after LD): {result['Final Roll']}\n"
                f"Threshold Value (TV): {result['Threshold Value (TV)']}\n"
                f"Level of Difficulty (LD): {result['Level of Difficulty (LD)']}\n"
                f"**Result: {result['Result']}**")
    
    await ctx.send(response)

bot.run(TOKEN)
