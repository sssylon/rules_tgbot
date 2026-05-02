# Rules TGBot

Telegram bot using aiogram to create votable rules in group chats.

Commands

- `/send_rules` (admin only) — send and set the main rules message the bot will edit when a rule is accepted.
- `/vote <text>` — create a 16-hour vote with inline buttons.
- `/close_vote <id>` — admin-only: close vote manually without accepting the rule.
- `/set_bot_count <n>` (admin only) — set how many bots are considered in the chat when computing the >50% threshold (default is 1, representing this bot).
- `/send_rules` (admin only) — send or update the rules message; shows accepted rules numbered from 1.
- `/add_rule <text>` (admin only) — add a rule immediately as accepted.
- `/remove_rule <n>` (admin only) — remove accepted rule number `n` (1-based).
- `/edit_rule <n> <text>` (admin only) — edit accepted rule number `n`.
- `/refresh_rules` (admin only) — rebuild or send the rules message from stored accepted rules.

Install and run (local)

1. Create a virtualenv and install dependencies:

   pip install -r requirements.txt

2. Create `.env` from `.env.example` and set `BOT_TOKEN` and `DATABASE_URL` (or use default in `.env.example` for Docker).

3. Run:

   python bot.py

Run with Docker (recommended for production)

1. Build and start services:

   docker-compose up -d --build

2. Logs:

   docker-compose logs -f bot

Notes

- The bot uses PostgreSQL in production via `DATABASE_URL`.
- On startup the bot will run DB migrations from `migrations/init_db.sql`.
- Votes auto-close after 16 hours, and upon auto-close the rule is accepted if `За` >= 50%+1 of total members (excluding bots as configured via `/set_bot_count`).
- Bots are excluded from voting (bot callbacks ignored).
- Only admins can run `/send_rules` and `/close_vote`.

Security & Production notes

- In production set a strong password for Postgres and configure backups; do NOT use default credentials in production.
- Keep your `.env` with `BOT_TOKEN` out of version control. Use a secrets manager (Docker secrets, Kubernetes Secrets, HashiCorp Vault) where possible.
- Run the container as a non-root user (the Dockerfile creates a user `bot`), and avoid mounting sensitive host volumes into containers unless necessary.
- Consider running behind a network-restricted setup (private VPC / firewall rules) and enabling TLS for database connections.
- Rotate `BOT_TOKEN` and DB credentials periodically and revoke if compromised.
