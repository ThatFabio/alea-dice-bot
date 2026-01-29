# Bot Discord ALEA

Un bot Discord con slash command per il sistema di gioco di ruolo tabulare **ALEA GdR**. Esegue tiri di dadi con supporto dinamico per i Gradi di Successo.

## Funzionalità

- **`/alea vs:VALORE [ld:MODIFICATORE] [verbose:BOOLEANO]`** - Esegui tiri ALEA (1d100)
  - `vs` (Valore Soglia): Valore richiesto (obbligatorio)
  - `ld` (Livello Difficoltà): Modificatore difficoltà (-60 a +60, opzionale, default: 0)
  - `verbose` (Booleano): Mostra tutti i Gradi di Successo o solo il risultato (opzionale, default: false)

- **`/alea-help`** - Mostra la guida d'uso e documentazione sui Gradi di Successo in italiano

- **Tiro Aperto**: Reroll automatici su tiri critici (1-5, 96-100)

- **Livelli Successo Configurabili**: Modifica `thresholds.csv` per personalizzare i Gradi di Successo per campagna

## Distribuzione Attuale

**Piattaforma**: Oracle Cloud Free Tier (Istanza Compute Always-Free)  
**OS**: Ubuntu 22.04 LTS  
**IP Pubblico**: `80.225.89.179`  
**Servizio**: `alea-bot.service` (gestito da systemd)  
**Auto-Pull**: Ogni 5 minuti da GitHub (via cron)

### Stato del Servizio

```bash
# Controlla stato servizio
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl status alea-bot.service"

# Visualizza log recenti
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo journalctl -u alea-bot.service -n 50 -f"

# Riavvia manualmente
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl restart alea-bot.service"
```

## Inviare Aggiornamenti

### Workflow Standard (Consigliato)

Tutti gli aggiornamenti vengono distribuiti automaticamente entro **5 minuti**:

```bash
# Dalla tua macchina locale
cd alea-bot
git add .
git commit -m "Descrizione del cambio"
git push origin main
```

Il bot:
1. Rileva i cambiamenti via cron (ogni 5 minuti)
2. Esegue il pull da GitHub
3. Riavvia automaticamente il servizio systemd
4. Carica nuova configurazione (es. `thresholds.csv`)

### Distribuzione Istantanea da Cloud Shell

Se hai bisogno di distribuzione immediata (senza aspettare 5 minuti):

```bash
# Da Oracle Cloud Shell (o SSH)
ssh -i ~/ssh-private-key-2026-01-29.key ubuntu@80.225.89.179 << 'CMD'
cd /home/deploy/alea-dice-bot
sudo -u deploy git pull origin main
sudo systemctl restart alea-bot.service
CMD
```

### Upload Completa Directory (Override Emergenza)

Per rimpiazzare completamente la directory da Cloud Shell:

```bash
# Carica intero repo
scp -r -i ~/ssh-private-key-2026-01-29.key ~/alea-dice-bot ubuntu@80.225.89.179:/tmp/alea-dice-bot-new

# Rimpiazza e riavvia
ssh -i ~/ssh-private-key-2026-01-29.key ubuntu@80.225.89.179 << 'CMD'
sudo rm -rf /home/deploy/alea-dice-bot
sudo mv /tmp/alea-dice-bot-new /home/deploy/alea-dice-bot
sudo chown -R deploy:deploy /home/deploy/alea-dice-bot
sudo systemctl restart alea-bot.service
CMD
```

## Configurazione

### Gradi di Successo

Modifica `thresholds.csv` per personalizzare le categorie di successo. Formato:

```csv
percentuale_soglia, etichetta_completa, acronimo
10,Successo Assoluto,SA
70,Successo Pieno,SP
100,Successo Parziale,Sp
130,Fallimento Parziale,Fp
200,Fallimento Pieno,FP
999,Fallimento Critico,FC
```

- **Percentuale soglia**: Quando il tiro supera questa % del Valore Soglia
- **Etichetta completa**: Nome in italiano visualizzato in Discord
- **Acronimo**: Codice breve mostrato nei risultati

Il bot carica dinamicamente qualsiasi numero di livelli (6, 8, 10+). Aggiorna e fai il push per distribuire.

### Variabili d'Ambiente

- `DISCORD_BOT_TOKEN`: Token del tuo bot Discord (memorizzato nel servizio systemd)

## Struttura Repository

```
alea-bot/
├── main.py              # Entry point bot con slash command
├── requirements.txt     # Dipendenze Python (discord.py, flask)
├── thresholds.csv       # Configurazione livelli successo
├── deploy-oracle.sh     # Script distribuzione (riferimento)
└── README.md            # Questo file
```

## Dipendenze

- `discord.py` (2.6.4+) - Framework bot Discord
- `flask` - Server keep-alive per compatibilità Render (mantenuto per riferimento, non necessario su Oracle)
- Python 3.10+

## Sviluppo

### Test Locale

```bash
pip install -r requirements.txt
export DISCORD_BOT_TOKEN="your_token_here"
python3 main.py
```

### Distribuire Cambiamenti

1. **Modifica codice localmente** (main.py, thresholds.csv, ecc.)
2. **Test localmente** con variabile d'ambiente
3. **Commit e push**:
   ```bash
   git add .
   git commit -m "Descrizione"
   git push origin main
   ```
4. **Aspetta 5 minuti** per auto-pull e riavvio (o forza immediatamente con comando SSH)

## Risoluzione Problemi

### Bot non risponde ai comandi

Controlla i log:
```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo journalctl -u alea-bot.service -n 100 | grep -i error"
```

### Riavvio manuale servizio

```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo systemctl restart alea-bot.service"
```

### Visualizza soglie caricate dal bot

Controlla il file CSV sull'istanza:
```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "sudo -u deploy cat /home/deploy/alea-dice-bot/thresholds.csv"
```

### Forza aggiornamento immediato da GitHub

```bash
ssh -i YOUR_KEY.key ubuntu@80.225.89.179 "cd /home/deploy/alea-dice-bot && sudo -u deploy git pull origin main"
```

## Architettura Sistema

**Flusso Distribuzione:**
```
GitHub (alea-dice-bot)
    ↓
Cron job (ogni 5 min): git pull + systemctl restart
    ↓
/home/deploy/alea-dice-bot/main.py
    ↓
Servizio systemd (alea-bot.service)
    ↓
API Discord → Tuo Server
```

**Always-On**: Systemd gestisce riavvio su crash (`Restart=always`, `RestartSec=10`)

## Licenza

Parte del sistema ALEA GdR

## Supporto

Per problemi, controlla i log sull'istanza Oracle o rivedi le istruzioni di distribuzione sopra.
