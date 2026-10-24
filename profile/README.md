<div align="center">

<a href="https://discord.gg/REPLACE_ME"><img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/banner.svg" alt="PUGZ. Pick-up games, run properly. Launching soon. Join the Discord." width="900"></a>

<br>

**PUGZ** is a community for pick-up games in *THE FINALS*.<br>
A Discord bot runs the queues, lobbies and matches. A website keeps score.<br>
Everything in between is built to be fast, fair and restart-proof.

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-platform.svg" alt="The platform">

## One community. Two surfaces. Always in sync.

</div>

<table>
<tr>
<td width="50%" valign="top">

### On Discord
**The bot runs the match.**

- **Queues that stay live.** One panel, one click to join or leave, and a ping when a queue is a player short.
- **Lobbies in seconds.** When a queue pops, joining the voice channel is the ready-up. Vote the map, pick a host, share the lobby code. No-shows are replaced from the queue.
- **Live matches.** Team voice channels, team panels, substitutes and a button to call staff.
- **Results without arguments.** One team reports, the other confirms. Disputes go to staff, who can set, void or correct a result with a reason on record.
- **Rematches.** Run it back with the same teams or shuffled, or go straight back to the queue.
- **Support.** Tickets in private channels, player reports with the match attached, full transcripts.

</td>
<td width="50%" valign="top">

### On the web
**The website keeps score.**

- **Leaderboards by season.** Podium, movement since yesterday, form and player search.
- **Player profiles.** PUG rating, match history, your THE FINALS rank, linked Steam, Twitch and Embark accounts, and a bio.
- **Match pages.** The full story of every game, from the pop to the final score.
- **A staff portal.** Manage live and finished matches, queues, bans and tickets. Access follows Discord roles, and every change lands in an audit log.
- **One login.** Sign in with Discord. No new account to make.

</td>
</tr>
</table>

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-flow.svg" alt="How a match works">

## From queue to leaderboard

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/flow.svg" alt="How a match works. 1. Queue: join from Discord or the site. 2. Lobby: the queue pops, join the voice channel to ready up, then vote the map. 3. Match: team voice channels, a host and a lobby code. 4. Result: one team reports, the other confirms, disputes go to staff. 5. Rank: your rating, the season and the leaderboard move with every result." width="900">

<sub>Every step is recorded. If the bot restarts mid-match, it picks up exactly where it left off.</sub>

<br><br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-fair.svg" alt="Built to be fair">

## Fair by design, not by promise

</div>

| Principle | What it means |
|---|---|
| **Fair play first** | No-shows get an escalating queue ban and are replaced on the spot. A result stands only when the other team confirms it or staff decide it. |
| **Restarts are invisible** | Every queue, match and timer lives in the database, not in memory. A restart or a deploy doesn't cancel your game. |
| **Staff have receipts** | A full timeline for every match, a case for every moderation action and an audit log for every portal change. |
| **Clear by default** | The click is the answer. Joining a queue is one button, with no extra message to dismiss. |
| **Your data, your call** | Player data can be erased on request. Privacy is part of the platform, not an afterthought. |

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-rating.svg" alt="Ratings and seasons">

## A rating that means something

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/ranks.svg" alt="Every rank, one community. Bronze, Silver, Gold, Platinum, Diamond and Ruby." width="900">

</div>

<br>

- **Every season starts at 1000.** A 2-0 moves your PUG rating more than a 2-1.
- **Placements are quick.** The first 10 matches of a season move faster, so you find your level fast.
- **Leaving costs you.** Leave a running match and you take the loss if your team loses.
- **Mistakes get fixed.** Corrections, voids and late disputes recalculate the season automatically.
- **Seasons are fresh starts.** Staff start each season, and a match counts for the season it began in, so a new season never reshuffles old results.

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-status.svg" alt="Where we are">

## Where we are

</div>

PUGZ is in **pre-launch**. The core platform is built and being tested end to end on our own server. The public launch follows.

| Area | Where | Status |
|---|---|---|
| Queues and queue bans | Discord, web | In testing |
| Pre-match lobbies, ready-up and map votes | Discord | In testing |
| Live matches and team voice channels | Discord, web | In testing |
| Results, disputes and evidence | Discord, web | In testing |
| Post-match lobby and rematch | Discord | In testing |
| PUG ratings, seasons and leaderboards | Discord, web | In testing |
| Player profiles and linked accounts | Web | In testing |
| Support tickets and transcripts | Discord, web | In testing |
| Staff portal | Web | In testing |
| Custom scrims | Discord, web | **Next** |
| Teams and scrim scheduling | Discord, web | Planned |
| Tournaments | Discord, web | Planned |
| Coaching | Web | Planned |

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-stack.svg" alt="Under the hood">

## Under the hood

</div>

Three programs share one database. The bot is the only writer of match data, so the website can ask for a change but never make one behind the bot's back.

```mermaid
%%{init: {'theme':'base','themeVariables':{'primaryColor':'#0d0d26','primaryTextColor':'#f0f0fb','primaryBorderColor':'#9b5cff','lineColor':'#4c6bff','secondaryColor':'#121233','tertiaryColor':'#070719','fontFamily':'system-ui, sans-serif'}}}%%
flowchart LR
  P([Players and staff]) --> D[Discord]
  P --> W[Website and staff portal]
  D --> B[Bot]
  W -- commands --> B
  B --> DB[(PostgreSQL)]
  W --> DB
  J[Worker] --> DB
```

| Layer | Technology |
|---|---|
| **Language** | TypeScript, strict, in one monorepo |
| **Bot** | Node.js 24, discord.js v14, Components v2 |
| **Website** | Fastify 5, React 19, Vite, Tailwind CSS v4 |
| **Database** | PostgreSQL 18, Prisma |
| **Background jobs** | pg-boss, running on the same database |
| **Quality** | vitest integration tests against a real database, including restarts and races |
| **Designed for** | 100+ players in queues and matches at once |

<div align="center">

<br>

<a href="https://discord.gg/REPLACE_ME"><img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/cta.svg" alt="Your next match is one click away. Join the Discord, link your Embark name and take a seat in the queue." width="900"></a>

<sub>Questions, bugs or ideas? Open a ticket in the Discord.</sub>

<br><br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/wordmark.svg" alt="PUGZ" width="900">

<br>

<sub>PUGZ is an independent community project. Not affiliated with Embark Studios.</sub><br>
<sub>THE FINALS and Embark Studios are trademarks of their respective owners.</sub><br>
<sub>&copy; 2026 PUGZ</sub>

</div>
