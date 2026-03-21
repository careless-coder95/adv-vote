# 🎉 Telegram Giveaway Bot

A powerful Telegram Giveaway Bot with live voting, leaderboard, paid voting system, and much more!

---

## 📁 File Structure

```
giveaway_bot/
│
├── bot.py                  → Main entry point
├── config.py               → Token, MongoDB URI, links
├── database.py             → MongoDB collections setup
├── utils.py                → Helper functions
├── font.py                 → Special unicode font
├── requirements.txt        → Python dependencies
├── README.md               → This file
│
└── handlers/
    ├── __init__.py         → Package init (empty file)
    ├── start.py            → /start + menu buttons
    ├── create_giveaway.py  → New giveaway creation flow
    ├── giveaway.py         → Join, verify, free vote, leave detection
    ├── paid_voting.py      → Paid votes, QR, approve/decline
    ├── my_giveaway.py      → My giveaways, leaderboard, stats, end
    └── router.py           → Smart message router
```

---

## 🖥️ Requirements

### Python Version
```
Python 3.10 or above (Recommended: 3.11 / 3.12)
```

Check your version:
```bash
python --version
```

Download: https://www.python.org/downloads/

### Libraries

| Library | Version | Use |
|---------|---------|-----|
| `python-telegram-bot` | 20.7 | Telegram Bot API |
| `pymongo` | 4.6.1 | MongoDB database |

---

## ⚙️ Installation

```bash
# Step 1 — Install dependencies
pip install -r requirements.txt

# Step 2 — Fill config.py

# Step 3 — Run
python bot.py
```

**Virtual Environment (Recommended):**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python bot.py
```

---

## 🔧 Configuration

Fill these in `config.py`:

```python
BOT_TOKEN         = "YOUR_BOT_TOKEN"        # From BotFather
MONGO_URI         = "YOUR_MONGODB_URI"      # MongoDB Atlas string
WELCOME_IMAGE_URL = "YOUR_IMAGE_URL"        # Catbox image URL (/start + channel posts)
SUPPORT_URL       = "https://t.me/CarelessxWorld"
UPDATE_URL        = "https://t.me/ll_CarelessxCoder_ll"
OWNER_URL         = "https://t.me/CarelessxOwner"
```

### BOT_TOKEN
1. Open [@BotFather](https://t.me/BotFather)
2. Send `/newbot` → give name and username
3. Copy the token

### MONGO_URI (MongoDB Atlas — Free)
1. Go to https://cloud.mongodb.com → Create free cluster (M0)
2. Connect → Drivers → Copy string:
   ```
   mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```

### Your Telegram ID
Open [@userinfobot](https://t.me/userinfobot) → `/start` → copy your ID

---

## 🤖 Bot Permissions (in Channel)

Make bot admin with:
- ✅ Post Messages
- ✅ Edit Messages
- ✅ Delete Messages
- ✅ Add Members *(for leave vote detection)*

---

## 📌 Commands

| Command | Description |
|---------|-------------|
| `/start` | Open main menu |
| `/cancel` | Cancel any ongoing action |

---

## 🚀 How to Use

### Creating a Giveaway:
```
1. /start → New Giveaway
2. Send description (text or photo)
3. Send channel ID or @username (bot must be admin)
4. Send target channel link (participants will join this)
5. Choose voting: Free / Paid / Both
6. If paid → send UPI QR photo
7. Set rate: ₹1 = how many votes?
8. Set minimum votes (or 0 to skip)
9. Get join link → share with participants!
```

### Participant Flow:
```
1. Click join link → bot opens
2. Click "Join Channel"
3. Click "Verify & Submit"
4. Details posted in channel with vote button + welcome image
5. Success message shows channel link + post link
6. Share post link to get votes!
```

### Voting Rules:
- One free vote per user per giveaway
- If user votes for someone else → previous vote removed automatically
- Channel leave → free vote removed automatically
- Paid votes can be bought separately

### Paid Voting:
```
1. Click "Buy Paid Votes" in bot
2. Enter ₹ amount
3. Votes auto-calculated (amount × rate)
4. QR shown → make payment
5. Send screenshot
6. Creator approves → votes added + channel announcement
```

### My Giveaway:
```
→ Click any giveaway → options appear:
   🏆 Leaderboard   — Live vote rankings
   📊 Stats         — Participants, votes, revenue
   ⏸️ Pause/Resume  — Stop/start voting
   ✏️ Edit          — Change description or QR
   🏁 End Giveaway  — Post results, notify all participants
```

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎉 Multiple Giveaways | Many giveaways running at same time |
| 🗳️ Free Voting | One vote, change allowed (old vote auto-removed) |
| 💰 Paid Voting | Buy votes via UPI QR |
| 🔀 Free + Paid | Both together |
| 🚪 Leave = Minus | Channel leave removes free vote |
| 🖼️ Welcome Image | Image posted with participant details in channel |
| 🏆 Leaderboard | Live rankings |
| 📊 Stats | Revenue, votes, participants |
| ⏸️ Pause/Resume | Temporarily stop voting |
| ✏️ Edit Giveaway | Update description or QR anytime |
| 🎯 Min Votes | Minimum votes to allow ending |
| 🔔 Vote Notification | Participant notified on new vote |
| 🎊 End Notification | All participants notified with rank on end |
| 🏅 Winner Message | Winner gets special congratulations message |

---

## 🗄️ MongoDB Collections

| Collection | Data |
|-----------|------|
| `users` | Bot users |
| `giveaways` | Giveaway settings and info |
| `participants` | Verified participants per giveaway |
| `votes` | Free and paid votes |
| `payments` | Payment requests and status |

---

## 🗂️ GitHub Upload Structure

```
giveaway_bot/          ← Root folder on GitHub
│
├── bot.py
├── config.py
├── database.py
├── utils.py
├── font.py
├── requirements.txt
├── README.md
│
└── handlers/          ← Subfolder
    ├── __init__.py
    ├── start.py
    ├── create_giveaway.py
    ├── giveaway.py
    ├── paid_voting.py
    ├── my_giveaway.py
    └── router.py
```

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Token correct? `python bot.py` running? |
| Post not going to channel | Bot admin? All permissions given? |
| Vote not removing on leave | "Add Members" permission given to bot? |
| MongoDB error | Atlas → Network Access → Add `0.0.0.0/0` |
| ModuleNotFoundError | `pip install -r requirements.txt` |
| Python error | Use Python 3.10 or above |

---

## 📞 Support

- 🛠️ Support: https://t.me/CarelessxWorld
- 📢 Updates: https://t.me/ll_CarelessxCoder_ll
- 👑 Owner: https://t.me/CarelessxOwner
