# 🎉 Telegram Giveaway Bot

Ek powerful Giveaway Bot — multiple giveaways, free + paid voting, live leaderboard, aur bahut kuch!

---

## 📁 Project Structure

```
giveaway_bot/
│
├── bot.py                    # Main entry point — yahan se bot start hota hai
├── config.py                 # BOT_TOKEN, MONGO_URI aur baaki config
├── database.py               # MongoDB collections setup
├── utils.py                  # Helper functions
├── requirements.txt          # Python dependencies
│
└── handlers/
    ├── __init__.py
    ├── start.py              # /start aur menu buttons
    ├── create_giveaway.py    # Naya giveaway banane ka flow
    ├── giveaway.py           # Join, verify, free vote, channel leave
    ├── paid_voting.py        # Paid votes — QR, screenshot, approve/decline
    ├── my_giveaway.py        # My giveaways, leaderboard, end giveaway
    └── router.py             # Smart message router
```

---

## 🖥️ Requirements

```
Python 3.10+
python-telegram-bot==20.7
pymongo==4.6.1
```

---

## ⚙️ Configuration

`config.py` mein yeh values bharo:

```python
BOT_TOKEN         = "YOUR_BOT_TOKEN"        # BotFather se
MONGO_URI         = "YOUR_MONGODB_URI"      # MongoDB Atlas
WELCOME_IMAGE_URL = "YOUR_IMAGE_URL"        # Catbox image URL
SUPPORT_URL       = "https://t.me/..."
OWNER_URL         = "https://t.me/..."
```

---

## 🚀 GitHub Par Setup Kaise Karo

### Step 1 — GitHub Account
https://github.com par account banao (agar nahi hai to)

### Step 2 — New Repository Banao
1. GitHub par jaao → `+` button → `New repository`
2. Name: `giveaway-bot`
3. Private select karo (recommended — token safe rahe)
4. `Create repository` click karo

### Step 3 — Files Upload Karo
**Option A — GitHub Website se (Easy):**
1. Repository mein jaao
2. `Add file` → `Upload files`
3. Saari files drag karke upload karo
4. `Commit changes` click karo

**Option B — Git se (Advanced):**
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/TUMHARA_USERNAME/giveaway-bot.git
git push -u origin main
```

### Step 4 — Bot Chalao (VPS/Server par)

**Local machine par:**
```bash
git clone https://github.com/TUMHARA_USERNAME/giveaway-bot.git
cd giveaway-bot
pip install -r requirements.txt
python bot.py
```

**VPS par (24/7 chalane ke liye):**
```bash
# Dependencies install karo
pip install -r requirements.txt

# Background mein chalao
nohup python bot.py &

# Ya screen use karo
screen -S giveaway_bot
python bot.py
# Ctrl+A phir D se detach karo
```

**Systemd Service (Best for VPS):**
```bash
# /etc/systemd/system/giveaway_bot.service file banao
[Unit]
Description=Giveaway Bot
After=network.target

[Service]
WorkingDirectory=/path/to/giveaway_bot
ExecStart=/usr/bin/python3 bot.py
Restart=always

[Install]
WantedBy=multi-user.target

# Enable karo
systemctl enable giveaway_bot
systemctl start giveaway_bot
```

---

## 📌 Bot Use Karne Ka Flow

### Giveaway Creator:
```
1. /start → New Giveaway button
2. Description likho (text + optional photo)
3. Channel ID do (bot wahan admin hona chahiye)
4. Target channel link do (participants join karenge)
5. Voting type choose karo (Free / Paid / Both)
6. Agar paid → QR photo bhejo
7. Rate set karo (₹1 = kitne votes)
8. Join link milega → participants ko bhejo!
```

### Participant:
```
1. Join link click karo
2. Channel join karo
3. Verify & Submit dabao
4. Channel mein tumhari details post ho jayegi
5. Vote button lag jayega
6. Agar paid voting → Buy Paid Votes se khareed sakte ho
```

### Free Vote:
- Channel mein emoji button dabao → vote ho gaya
- Channel leave karo → vote minus ho jayega

### Paid Vote:
```
1. Bot mein Buy Paid Votes dabao
2. Amount likho (₹ mein)
3. Auto calculate hoga kitne votes milenge
4. QR dikhega → payment karo
5. Screenshot bhejo bot mein
6. Creator approve kare → votes add + channel mein announcement
```

### Giveaway End:
```
My Giveaway → Giveaway select → End Giveaway
→ Final results channel mein post ho jayenge
→ Winner announce hoga
```

---

## 🗄️ MongoDB Collections

| Collection | Data |
|-----------|------|
| `users` | Bot users |
| `giveaways` | Giveaway info, settings |
| `participants` | Verified participants per giveaway |
| `votes` | Free + paid votes |
| `payments` | Payment requests + status |

---

## ⚠️ Bot Permissions (Channel mein)
- ✅ Post Messages
- ✅ Edit Messages
- ✅ Delete Messages
- ✅ Add Members

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot respond nahi kar raha | Token sahi hai? `python bot.py` chal raha hai? |
| Channel mein post nahi ho rahi | Bot channel admin hai? Permissions sahi hain? |
| Vote minus nahi hota | Bot ko Add Members permission di? |
| MongoDB error | Atlas mein IP `0.0.0.0/0` whitelist karo |
| ModuleNotFoundError | `pip install -r requirements.txt` |
