# Galaxy Gamez Poster - v1 Update Notes

## Files: what to do with each
**NEW files (add these to your repo):**
- `config.py`
- `storage.py`
- `telegram_api.py`
- `caption.py`

**REPLACE these (overwrite the old ones):**
- `main.py`
- `bot_commands.py`
- `.github/workflows/commands.yml`
- `.github/workflows/post.yml`

**Leave alone / auto-created on first run:**
- `state.json`, `stats.json`, `last_run_log.txt` - unchanged format
- `posted_posts.json` - keep it, it's used ONCE to migrate your old history into the new system, then you can delete it after the first successful run
- `users.json`, `broadcasts.json` - new files, created automatically the first time the bot runs, don't create manually

No new GitHub Secrets needed - same 3 you already have (`TELEGRAM_BOT_TOKEN`, `ADMIN_CHAT_ID`, `GITHUB_TOKEN`).

## Bug fixed
Old code posted 3 random unposted games per cycle, and only marked a post as
"done" if ALL 6 channels succeeded - so one failed channel caused a repeat
send to the other 5. New code: strict oldest-to-newest order, 1 post per
channel per cycle, and each channel tracks its own history separately so a
failed send never causes a repeat elsewhere.

## New features
1. **Multi-user** - anyone can DM the bot, tap "➕ Add Channel", make the bot
   admin in their channel, then "📰 Add Blog" to set their Blogger feed. Their
   channel auto-posts every 3hrs from then on, same as yours.
2. **New post caption format** - applied automatically, uses your new
   bold-unicode layout.
3. **Keyboard buttons** - every command now has a button, admin sees a
   bigger menu (Broadcast, Users, Pause/Resume everyone, Advanced submenu for
   Reset/Logs). Regular users see a smaller menu scoped to just their channel.
4. **Force-join gate** - nobody can use ANY command until they've joined
   your 2 channels + 2 groups. Bot shows join buttons + a recheck button.
5. **Admin broadcast** - tap "📢 Broadcast", send your ad/promo text, it goes
   out to every connected channel. This is your paid-promo lever.
6. **Strike/ban system** - if a user deletes a broadcast post within 4hrs,
   their channel is auto-removed and they get a strike. 3 strikes = permanent
   ban from ever adding a channel again. They're told this upfront when they
   add their channel, and reminded in /help.
7. **Credits: @galaxygamezsupport** - added to help, onboarding, and
   strike/ban messages.

## First deploy checklist
1. Push all files above to your repo.
2. Manually trigger the "Check Admin Commands" workflow once (Actions tab →
   Run workflow) so `users.json` gets created and your 6 channels + old
   history migrate in.
3. DM your bot `/start` from your admin account to confirm the admin
   keyboard shows up.
4. Once confirmed working for a day, delete `posted_posts.json`.
