import discord
from discord.ext import commands
import random
import os

TOKEN = os.getenv("DISCORD_BOT_TOKEN")  # Load token from Render's environment variables

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="/", intents=intents)

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
