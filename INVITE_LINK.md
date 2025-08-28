# BananaBot Discord Invite Links

## 🔗 Correct Invite Links

### **Full Permissions (Recommended)**
```
https://discord.com/oauth2/authorize?client_id=1410744225120915498&permissions=274877910080&scope=bot%20applications.commands
```

### **Minimal Permissions (Basic)**
```
https://discord.com/oauth2/authorize?client_id=1410744225120915498&permissions=117760&scope=bot%20applications.commands
```

## ⚙️ Required Permissions Breakdown

### **Full Permissions (274877910080)**
- Send Messages
- Attach Files  
- Use Slash Commands
- Read Message History
- View Channels
- Add Reactions
- Use External Emojis

### **Minimal Permissions (117760)**
- Send Messages
- Attach Files
- Use Slash Commands

## 🚨 Why Your Link Didn't Work

Your original link was missing:
1. **`scope=bot applications.commands`** - Required for Discord bots
2. **`permissions=XXXXXX`** - Required permission flags
3. **Proper URL encoding** - Spaces need to be encoded as `%20`

## 🔧 How to Generate Links Manually

1. Go to [Discord Developer Portal](https://discord.com/developers/applications/1410744225120915498/oauth2/url-generator)
2. Under **Scopes**, select:
   - ✅ `bot`
   - ✅ `applications.commands`
3. Under **Bot Permissions**, select:
   - ✅ Send Messages
   - ✅ Attach Files
   - ✅ Use Slash Commands
4. Copy the generated URL

## 📱 Step-by-Step Bot Setup

1. **Use the Full Permissions link above**
2. **Select your Discord server**
3. **Click "Authorize"**
4. **Start your bot**: `python start.py`
5. **Wait for "BananaBot is ready!" message**
6. **Test with**: `/generate prompt: "test image"`

## ⚠️ Troubleshooting

### Bot Joins but Commands Don't Appear
- Make sure bot is running (`python start.py`)
- Wait up to 5 minutes for commands to sync
- Check bot logs for "Commands synced" message

### "Application did not respond" Error
- Bot needs to be online when commands are used
- Check `.env` file has correct tokens
- Verify bot has proper permissions

### Commands Appear but Don't Work
- Check bot logs for error messages
- Verify API keys are correct in `.env`
- Ensure bot has internet access

## 🎯 Quick Test

After inviting the bot:
1. Type `/` in any channel
2. Look for BananaBot commands
3. Try: `/generate prompt: "a beautiful sunset"`
4. Bot should respond with "Image generation in progress..."

**Use the Full Permissions link above to properly invite your bot! 🍌**