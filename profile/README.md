<div align="center">

<a href="https://discord.gg/Sa5j37WDR"><img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/banner.svg?v=6218add2" alt="PUGZ. Pick-up games for THE FINALS. In pre-launch testing. Join the Discord." width="900"></a>

<br>

**PUGZ** is a community platform at its core for pick-up games in *THE FINALS*.<br><br>
Join queues and play matches through Discord, then track your rating, results and match history on the website.<br><br>
The platform also brings together team management, scrim scheduling, tournaments and coaching. Features are in testing or development; the status of each area is listed below.

For the future we have plans to expand and allow the bot in servers of other communities, creating a global ecosystem with shared queues, leaderboards, server competitions and much more.

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-platform.svg?v=eeaa2df6" alt="The platform">

## Discord for matches. The website for everything around them.

</div>

<table>
<tr>
<td width="50%" valign="top">

### On Discord
**Queues, match coordination and support in Discord.**

- **Match queues.** One panel, one click to join or leave, and a ping when a queue is a player short.
- **Pre-match lobbies.** When a queue fills, join the lobby voice channel to confirm you are ready. Vote on a map, select a host and share the lobby code. Players who miss the ready check are replaced from the queue.
- **Live matches.** Team voice channels, team panels, substitutes and a button to call staff.
- **Result reporting.** One team reports, the other confirms. Disputes go to staff, who can set, void or correct a result with a reason on record.
- **Rematches.** Run it back with the same teams or shuffled, or go straight back to the queue.
- **Tournaments and scrims.** Brackets, match rooms and scrim blocks, all run by the bot.
- **Support.** Tickets in private channels, player reports with the match attached, full transcripts.

</td>
<td width="50%" valign="top">

### On the web
**Ratings, player profiles and community tools on the website.**

- **Leaderboards by season.** Podium, movement since yesterday, form and player search.
- **Player profiles.** PUG rating, match history, your THE FINALS rank, linked Steam, Twitch and Embark accounts, and a bio.
- **Match pages.** A timeline of each match, from lobby creation to the confirmed result.
- **Teams, tournaments and coaching.** Rosters, live brackets and a coach directory, all tied to the profile you already have.
- **A staff portal.** Manage live and finished matches, queues, bans and tickets. Access follows Discord roles, and every change lands in an audit log.
- **One login.** Sign in with Discord. Use your existing Discord account to access the platform.

</td>
</tr>
</table>

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-flow.svg?v=2b23bc1d" alt="How a match works">

## From queue to leaderboard

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/flow.svg?v=eeba9a46" alt="How a match works. 1. Queue: join from Discord or the site. 2. Lobby: the queue pops, join the voice channel to ready up, then vote the map. 3. Match: team voice channels, a host and a lobby code. 4. Result: one team reports, the other confirms, disputes go to staff. 5. Rank: your rating, the season and the leaderboard move with every result." width="900">

<sub>Match progress is saved so active matches can resume after a bot restart.</sub>

<br><br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-fair.svg?v=e0b407e2" alt="Built to be fair">

## Match rules and moderation

</div>

| Area | How it works |
|---|---|
| **Missed ready checks and disputed results** | Players who miss a ready check are replaced and receive escalating penalties for repeat offences. Results require confirmation from the opposing team or a staff decision. |
| **Saved match progress** | Queues, matches and timers are stored in the database so they can be restored after a restart or deployment. |
| **Moderation records** | Staff can review match timelines, moderation cases and an audit log of changes made through the staff portal. |
| **Queue controls** | Join or leave a queue using its buttons. The queue panel updates to show the current players. |
| **Data deletion** | Players can request deletion of their player data. |

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-rating.svg?v=5b4fddf8" alt="Ratings and seasons">

## PUG ratings and seasons

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/rating.svg?v=303f5c43" alt="How the PUG rating works. Each scoreline is worth its own points, beating a stronger team pays more, your first matches of a season move your rating further, and your rank changes the moment you cross a threshold." width="900">

<br><br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/tiers.svg?v=41348d5b" alt="The PUG rating ladder: Rookie below 750, Prospect 750, Contender 850, Challenger 950, Pro 1050, Elite 1150, Star 1250, All-Star 1350, Superstar 1500 and Legend 1650." width="900">

</div>

<br>

- **Ranks on Discord and the website.** Your rank appears as a Discord role, a profile badge and a leaderboard entry. Roles include the rating threshold, such as Pro (1050+), and rank changes are shown in the post-match panel.
- **Promotions and demotions.** Your rank changes as soon as your rating crosses a rank threshold.
- **Season settings.** Each season has its own starting rating, points per scoreline, team-strength adjustments, placement settings and ranks. Changes to rating rules trigger a recalculation for that season.
- **Placement matches.** Complete the season's required placement matches to appear on the leaderboard.
- **Leaving a match.** If you leave an active match, you still receive a loss if your team loses.
- **Result corrections.** Corrections, voids and late disputes recalculate the season automatically.
- **Season resets.** Everyone starts unranked, rank roles are cleared and re-earned, and past seasons stay browsable with their own ranks. A match counts for the season it began in.
- **Cash prizes.** We aim to give away cash prizes for the top spots on the leaderboard every season, as well as in the tournaments we host ourselves. Prizes can also be given away as Multibucks codes.

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-teams.svg?v=5aea2e9c" alt="Teams and scrims">

## Teams and scrim scheduling

</div>

<table>
<tr>
<td width="50%" valign="top">

### Teams
**Manage your roster and track your team's activity.**

- **Rosters.** A captain, players and subs, with your team tag on every profile. Players apply or join by invite link.
- **Team pages.** Season stats, recent matches, trophies, a career timeline and a recruiting note.
- **Stay in touch.** Team chat and an inbox that also reaches you by Discord DM.
- **Connections.** Connect two teams and they can challenge each other directly.

</td>
<td width="50%" valign="top">

### Scrims
**Arrange practice matches with other teams.**

- **Find opponents.** Post when your team is free, send requests and challenges, and set a minimum rank.
- **3v3 and 12 Mans.** Both formats, with stand-ins when someone drops.
- **Run by the bot.** Each scrim gets a category, a locked text channel and a voice channel per side.
- **Feedback and history.** Teams can submit blind behaviour ratings after a scrim. Completed scrims are recorded in the team's history.

</td>
</tr>
</table>

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-tournaments.svg?v=7dc8483d" alt="Tournaments">

## Community tournaments

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/tournaments.svg?v=ed2915ae" alt="A tournament moves from registration to check-in to live to completed. A bracket of eight seeds runs quarter-finals, semi-finals and a final, and the champion is recorded on every profile." width="900">

</div>

<br>

Community tournaments run by the bot: sign up in Discord or on the site, check in before the start, and follow every bracket as results come in.

Third-party tournament organizers also host tournaments on PUGZ with real prize money.

- **Tournament formats.** Single and double elimination, round robin and Swiss, or groups into playoffs. Seeding and brackets are automatic.
- **Sign up your team.** Register on the site or with a join code in Discord. Check-in opens before the start, and a waitlist holds the spare teams.
- **A room for every match.** Report, confirm or dispute the result, with a map veto where the format calls for it.
- **Entry fees.** Optional. The captain pays on the site, the spot is held while they do, and a failed or cancelled entry is refunded automatically.
- **Host your own.** Other communities can run their tournaments with the PUGZ bot on their own server.
- **Prizes and history.** Prize pools are listed before registration. Tournament winners receive a Discord role, and their results are recorded on team and player profiles.

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-coaching.svg?v=19dd4b98" alt="Coaching">

## Individual coaching and VOD reviews

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/coaching.svg?v=14771547" alt="A verified coach with specialties and reviews, a calendar showing the next free slot, and a booking that moves from requested to confirmed, paid, completed and reviewed." width="900">

</div>

<br>

Coaching on PUGZ is built for both sides: players who want to improve, and coaches looking for a place to offer paid sessions. Coaches set their own schedules, accept or decline sessions and choose their own prices. PUGZ provides the infrastructure and the players to make it work.

<br>

Browse staff-approved coaches for one-on-one sessions and VOD reviews. Compare their experience, specialties, packages and availability before booking.

- **Staff-approved coaches.** Staff review coaches before they are listed. Profiles show their verified peak league, session reviews and specialties, including Light, Medium, Heavy, aim, game sense, team play and VOD review.
- **Availability and packages.** Coaches publish weekly availability, you see the next free slot up front and book instantly. Packages say how long they run and what is included.
- **Payments and payouts.** Checkout runs through Stripe and card details never touch our servers. The coach sells the session and PUGZ takes a fee. The coach's payout is released after you confirm the session. Reported problems are reviewed before the payout is released.
- **Booking chat.** Chat with your coach about the booking before the session.
- **Session reviews.** Only players who finished a session can review, and coaches can reply.

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-status.svg?v=17d1f1e2" alt="Development status">

## Development status

</div>

PUGZ is in **pre-launch**. The core platform is built and being tested end to end on our own server. Public access will follow testing.

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
| Custom scrims | Discord, web | Planned |
| Teams and scrim scheduling | Discord, web | In testing |
| Tournaments | Discord, web | In progress |
| Coaching | Web | In testing |

<div align="center">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/divider.svg?v=d319395b" alt="" width="900">

<br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/eyebrow-stack.svg?v=75a1a06c" alt="Under the hood">

## Under the hood

</div>

The website, Discord bot and background worker share a PostgreSQL database. The bot manages all changes to match data; actions on the website are sent to it as commands. Database notifications keep the services updated, while a durable job queue handles background tasks and external integrations.

<div align="center">

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/architecture.svg?v=b8d423fe" alt="How PUGZ fits together. Players and staff reach the website through Cloudflare and Nginx on the main droplet, and Discord talks to the bot over its gateway. The website sends commands to the bot and gets responses back. The website, the bot and the worker share one PostgreSQL database with change notifications. The worker, on its own droplet, processes the job queue and syncs with Embark, Steam, Twitch, Stripe, Resend and Liquipedia. A nightly encrypted backup goes off-site." width="900">

</div>

<br>

| Layer | Technology |
|---|---|
| **Language** | TypeScript, strict, in one monorepo |
| **Bot** | Node.js 24, discord.js v14, Components v2 |
| **Website** | Fastify 5, React 19, Vite, Tailwind CSS v4 |
| **Database** | PostgreSQL 18, Prisma |
| **Background jobs** | pg-boss, running on the same database |
| **Payments** | Stripe Connect for coaching |
| **Quality** | vitest integration tests against a real database, including restarts and races |
| **Designed for** | 100+ players in queues and matches at once |

<div align="center">

<br>

<a href="https://discord.gg/Sa5j37WDR"><img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/cta.svg?v=8b941803" alt="Join the PUGZ Discord for launch updates, community discussions and access when public queues open." width="900"></a>

<sub>Questions, bugs or ideas? Open a ticket in the Discord.</sub>

<br><br>

<img src="https://raw.githubusercontent.com/PUGZ-GG/.github/main/profile/assets/wordmark.svg?v=11237dbb" alt="PUGZ" width="900">

<br>

<sub>PUGZ is an independent registered business. Not affiliated with Embark Studios.</sub>

<sub>THE FINALS and Embark Studios are trademarks of their respective owners.</sub>

<sub>&copy; 2026 PUGZ</sub>

</div>
