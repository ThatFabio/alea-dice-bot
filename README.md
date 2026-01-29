# ALEA Discord Bot

A Discord slash command bot for the **ALEA GdR** tabletop RPG system. Executes dice rolls with dynamic Gradi di Successo (Degrees of Success) support.

## Features

- **`/alea tv:VALUE [ld:MODIFIER] [verbose:BOOL]`** - Execute ALEA dice rolls (1d100)
  - `tv` (Tiro Valore): Threshold Value (required)
  - `ld` (Livello Difficoltà): Difficulty modifier (-60 to +60, optional, default: 0)
  - `verbose` (Boolean): Show all success levels or just result (optional, default: false)

- **`/alea-help`** - Display usage guide and success level documentation in Italian

- **Tiro Aperto Support**: Automatic rerolls on critical rolls (1-5, 96-100)

- **Configurable Success Levels**: Edit `thresholds.csv` to customize the number of Gradi di Successo per campaign

## Current Deployment

**Platform**: Oracle Cloud Free Tier (Always-Free Compute Instance)  
**OS**: Ubuntu 22.04 LTS  
**Public IP**: `80.225.89.179`  
**Service**: `alea-bot.service` (systemd managed)  
**Auto-Pull**: Every 5 minutes from GitHub (via cron)

### Running Status

```bash
# Check service status
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl status alea-bot.service"

# View recent logs
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo journalctl -u alea-bot.service -n 50 -f"

# Manually restart
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl restart alea-bot.service"
```

## Pushing Updates

### Standard Workflow (Recommended)

All updates automatically deploy within **5 minutes**:

```bash
# From your local machine
cd alea-bot
git add .
git commit -m "Your change description"
git push origin main
```

The bot will:
1. Detect changes via cron (every 5 minutes)
2. Pull from GitHub
3. Auto-restart the systemd service
4. Load new configuration (e.g., `thresholds.csv`)

### Instant Deployment from Cloud Shell

If you need immediate deployment (don't want to wait 5 minutes):

```bash
# From Oracle Cloud Shell (or SSH)
ssh -i ~/ssh-private-key-2026-01-29.key ubuntu@80.225.89.179 << 'CMD'
cd /home/deploy/alea-dice-bot
sudo -u deploy git pull origin main
sudo systemctl restart alea-bot.service
CMD
```

### Full Directory Upload (Emergency Override)

For complete directory replacement from Cloud Shell:

```bash
# Upload entire repo
scp -r -i ~/ssh-private-key-2026-01-29.key ~/alea-dice-bot ubuntu@80.225.89.179:/tmp/alea-dice-bot-new

# Replace and restart
ssh -i ~/ssh-private-key-2026-01-29.key ubuntu@80.225.89.179 << 'CMD'
sudo rm -rf /home/deploy/alea-dice-bot
sudo mv /tmp/alea-dice-bot-new /home/deploy/alea-dice-bot
sudo chown -R deploy:deploy /home/deploy/alea-dice-bot
sudo systemctl restart alea-bot.service
CMD
```

## Configuration

### Gradi di Successo (Success Levels)

Edit `thresholds.csv` to customize success categories. Format:

```csv
percentage_threshold, full_label, acronym
10,Successo Assoluto,SA
70,Successo Pieno,SP
100,Successo Parziale,Sp
130,Fallimento Parziale,Fp
200,Fallimento Pieno,FP
999,Fallimento Critico,FC
```

- **Percentage threshold**: When roll exceeds this % of VS
- **Full label**: Italian name displayed in Discord
- **Acronym**: Short code shown in results

The bot dynamically loads any number of levels (6, 8, 10+). Update and push to deploy.

### Environment Variables

- `DISCORD_BOT_TOKEN`: Your Discord bot token (stored in systemd service)

## Repository Structure

```
alea-bot/
├── main.py              # Bot entry point with slash commands
├── requirements.txt     # Python dependencies (discord.py, flask)
├── thresholds.csv       # Success level configuration
├── deploy-oracle.sh     # Deployment script (reference)
└── README.md           # This file
```

## Dependencies

- `discord.py` (2.6.4+) - Discord bot framework
- `flask` - Keep-alive server for Render compatibility (kept for reference, not needed on Oracle)
- Python 3.10+

## Development

### Local Testing

```bash
pip install -r requirements.txt
export DISCORD_BOT_TOKEN="your_token_here"
python3 main.py
```

### Deploying Changes

1. **Edit code locally** (main.py, thresholds.csv, etc.)
2. **Test locally** with environment variable
3. **Commit and push**:
   ```bash
   git add .
   git commit -m "Description"
   git push origin main
   ```
4. **Wait 5 minutes** for auto-pull and restart (or force immediately with SSH command)

## Troubleshooting

### Bot not responding to commands

Check logs:
```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo journalctl -u alea-bot.service -n 100 | grep -i error"
```

### Manual service restart

```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl restart alea-bot.service"
```

### View thresholds loaded by bot

Check the CSV file on instance:
```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo -u deploy cat /home/deploy/alea-dice-bot/thresholds.csv"
```

### Force immediate update from GitHub

```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "cd /home/deploy/alea-dice-bot && sudo -u deploy git pull origin main"
```

## System Architecture

**Deployment Flow:**
```
GitHub (alea-dice-bot)
    ↓
Cron job (every 5 min): git pull + systemctl restart
    ↓
/home/deploy/alea-dice-bot/main.py
    ↓
systemd service (alea-bot.service)
    ↓
Discord API → Your Server
```

**Always-On**: Systemd handles restart on crash (`Restart=always`, `RestartSec=10`)

## License

Part of ALEA GdR system

## Support

For issues, check logs on Oracle instance or review deployment instructions above.
