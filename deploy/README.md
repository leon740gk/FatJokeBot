# Деплой на VPS (IONOS VPS S+, Ubuntu 24.04)

Бот работает через long polling, входящие порты ему не нужны. Хватает самого маленького тарифа (VPS S+: 1 vCore / 2 ГБ RAM).
Ниже `SERVER_IP` — адрес сервера из панели IONOS.

## 1. Заказать сервер

1. На ionos.de: VPS → самый дешёвый тариф (VPS S+), дата-центр в Германии, образ **Ubuntu 24.04**.
2. В Cloud Panel → Server → SSH Keys добавить свой публичный ключ (`cat ~/.ssh/id_ed25519.pub`;
   если ключа нет: `ssh-keygen -t ed25519`). Если ключ не добавлялся при заказе, пароль root будет в панели.
3. Network → Firewall Policies: оставить открытым только TCP 22 (SSH).

## 2. Подготовить сервер (под root)

```bash
ssh root@SERVER_IP
apt update && apt upgrade -y
apt install -y git sqlite3 unattended-upgrades
timedatectl set-timezone Europe/Berlin   # только для логов, расписание бота всегда по Киеву

# отдельный пользователь для бота, с тем же SSH-ключом
adduser --disabled-password --gecos "" bot
mkdir -p /home/bot/.ssh && cp ~/.ssh/authorized_keys /home/bot/.ssh/
chown -R bot:bot /home/bot/.ssh && chmod 700 /home/bot/.ssh && chmod 600 /home/bot/.ssh/authorized_keys

# боту можно только перезапускать свой сервис (для deploy/update.sh)
echo 'bot ALL=(root) NOPASSWD: /usr/bin/systemctl restart fat-joke' > /etc/sudoers.d/fat-joke
chmod 440 /etc/sudoers.d/fat-joke
```

Закрыть вход по паролю (сначала проверь, что `ssh bot@SERVER_IP` пускает по ключу из другого окна):

```bash
sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

## 3. Поставить бота (под bot)

```bash
ssh bot@SERVER_IP
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.local/bin/env
git clone https://github.com/leon740gk/FatJokeBot.git && cd FatJokeBot
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements.txt
cp .env.example .env && chmod 600 .env
nano .env   # вписать FAT_JOKE_BOT_TOKEN и FAT_JOKE_MAIN_CHAT_ID
mkdir -p telegram_bots/db_sqlite
```

## 4. Перенести базу с ноутбука

Сначала **останови бота на ноутбуке** (Ctrl+C): два бота с одним токеном мешают друг другу,
а копировать базу, в которую идёт запись, нельзя. Затем на ноутбуке, из корня проекта:

```bash
scp telegram_bots/db_sqlite/my_database.db bot@SERVER_IP:FatJokeBot/telegram_bots/db_sqlite/
```

## 5. Запустить как сервис (под root)

```bash
cp /home/bot/FatJokeBot/deploy/fat-joke.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now fat-joke
systemctl status fat-joke
journalctl -u fat-joke -f    # логи; выход Ctrl+C
```

Проверка: написать боту `/help` в чате. Сервис стартует сам после перезагрузки и поднимается после падения.

## Каждодневное

| Что | Команда |
|---|---|
| Обновить после `git push` | `ssh bot@SERVER_IP FatJokeBot/deploy/update.sh` |
| Логи | `ssh bot@SERVER_IP journalctl -u fat-joke -n 100` |
| Остановить / запустить (root) | `systemctl stop fat-joke` / `systemctl start fat-joke` |
| Забрать бэкапы на ноутбук | `scp -r bot@SERVER_IP:FatJokeBot/backups ./backups-server` |

Бэкапы бот делает сам каждый день в 04:00 по Киеву (14 последних в `~/FatJokeBot/backups`).
Они лежат на том же сервере, поэтому раз в неделю-две стоит забирать их на ноутбук.

Восстановить базу: `systemctl stop fat-joke`, скопировать нужный файл из `backups/` на место
`telegram_bots/db_sqlite/my_database.db`, `systemctl start fat-joke`.

Если поменял `.env`, нужно перезапустить: `sudo systemctl restart fat-joke`.
