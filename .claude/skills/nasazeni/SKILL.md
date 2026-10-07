---
name: nasazeni
description: Nasazení LKKL Log na server lety.lkkl.cz značkou v2.<modul>.<oprava> – kontroly, záloha serverové DB, zkouška migrace na kopii, značka, sledování GitHub Actions, ověření a řešení selhání. Použij, když uživatel řekne „nasaď v2.x.y“ (jen v projektu LKKL Log).
---

# Nasazení LKKL Log

Nasazuje se **jen na pokyn uživatele** a jen značkou `v2.<modul>.<oprava>` (CLAUDE.md → Nasazení).
Commit do `main` jen spustí kontroly v CI.

GitHub CLI není v PATH Git Bashe: `G="/c/Program Files/GitHub CLI/gh.exe"`.

## 1. Před značkou
1. `git status -s` – v `main` musí být commitnuté **jen moje změny**. Cizí soubory (např.
   rozpracované makety uživatele `docs/navrhy/*-desktop*.html`, `docs/modul-desktop.md`)
   nikdy necommitovat – při commitu přidávat soubory jmenovitě, ne `git add -A`.
2. Poslední běh CI v `main` zelený: `"$G" run list --branch main --limit 1`.
3. **Záloha serverové DB** (vždy, když se mění struktura; jinak doporučeně):
   ```bash
   F=/c/GIT/LKKLLog-zalohy/server-lkkllog-pred-v2.X.Y-$(date +%Y-%m-%d-%H%M).dump
   ssh one12 'runuser -u postgres -- pg_dump -Fc lkkllog' > "$F" && ls -la "$F"
   ```
4. **Nová migrace `db/NNN_*.sql` → povinně zkouška na kopii serverových dat** (skill
   `migrace-db`, kap. „Zkouška na kopii serveru“). v2.11.0 shodila server na 25 minut,
   protože migrace prošla lokálně, ale ne nad serverovými daty.

## 2. Značka a sledování
```bash
git tag v2.X.Y && git push -q origin v2.X.Y
sleep 10
id=$("$G" run list --branch v2.X.Y --limit 1 --json databaseId -q '.[0].databaseId')
"$G" run watch "$id" --exit-status >/dev/null 2>&1; echo "nasazení exit $?"
```
Běh má úlohy `server`, `frontend` (klikací testy), `image`, `deploy`. Obvykle 2–4 minuty.
Dlouhé čekání spouštěj na pozadí (`run_in_background`) a nepolluj.

## 3. Ověření
```bash
for i in 1 2 3 4 5 6 7 8; do r=$(curl -s -m 10 https://lety.lkkl.cz/api/health)
  case "$r" in *v2.X.Y*) echo "$r"; break;; esac; sleep 10; done
ssh one12 "runuser -u postgres -- psql -d lkkllog -X -A -t -c \"SELECT max(skript) FROM lkkl.migrace\"; docker ps --format '{{.Names}}|{{.Status}}' | grep lkkl"
```
Po startu kontejneru chvíli vrací 502 (migrace při startu) – to je normální.

## 4. Když to selže
| Příznak | Příčina | Co dělat |
|---|---|---|
| `deploy` selže: `ssh: connect to host one12.vas-server.cz port 22: Network is unreachable` | výpadek sítě GitHubu | `"$G" run rerun <id> --failed` |
| 502 déle než ~2 minuty, `max(skript)` se nezměnil | kontejner padá na migraci | `ssh one12 'docker logs --tail 40 vpsc-app-lkkl-cz-lkkllog'`; migrace běží v transakci, data jsou v pořádku. Opravit skript (dosud neprovedený na serveru), vyzkoušet na kopii, **nová značka** (např. v2.X.Y+1) – existující značku nepřepisovat |
| krok `npx playwright install` trvá minuty | pomalé zrcadlo Ubuntu | v CI už je bez `--with-deps` a s cache; neměnit zpět |
| `log-failed` | detail chyby | `"$G" run view <id> --log-failed \| tail -40` |

Výpadek nebo chybu uživateli řekni hned a otevřeně (co nejede, že data jsou v pořádku, co
dělám). Migraci na serveru **nikdy** nespouštět ručně přes psql.

## 5. Po nasazení
- Krátké shrnutí: verze běží, migrace, kde je záloha, co je nového.
- Aktualizovat paměť projektu (`project-lkkllog.md`: běžící verze, rozsah migrací).
