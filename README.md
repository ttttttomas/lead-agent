# Lead Agent

AI-powered lead generation and qualification agent for software agencies.

## Objective

Lead Agent discovers potential clients, analyzes their public web presence, scores opportunities, recommends the most relevant software service, stores leads in MySQL, and sends lead reports by email.

## Stack

- Frontend: Next.js + Tailwind CSS
- Backend: FastAPI
- Database: MySQL
- AI: Kimi K3 via NVIDIA API
- Discovery: OpenStreetMap + Nominatim + Overpass
- Notifications: Gmail SMTP

## Current flow

1. Search public business listings by industry and city.
2. Extract business name, website, email and phone when available.
3. Check MySQL to avoid processing known leads again.
4. If a website exists, scrape and analyze its public content.
5. If no website is available, analyze only the public listing facts.
6. Kimi K3 generates a 0-100 lead score, problems, opportunities, recommended service and outreach draft.
7. Store the analyzed lead in MySQL.
8. Send the analysis to the configured Gmail inbox.

## Structure

```text
lead-agent/
├── frontend/
├── backend/
├── database/
├── docs/
├── .gitignore
└── README.md
```

## Environment variables

Never commit real API keys or app passwords.

Backend (`backend/.env`):

```env
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
KIMI_MODEL=moonshotai/kimi-k3
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/lead_agent

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
NOTIFICATION_EMAIL=
```

Frontend:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

## Analyze one known website

`POST /api/leads/analyze`

```json
{
  "company": "Neptuno Viajes",
  "website": "https://neptuno.tur.ar/"
}
```

## Discover leads automatically

`POST /api/discovery/search`

```json
{
  "industry": "hoteles",
  "city": "Buenos Aires",
  "country": "Argentina",
  "limit": 10,
  "minimum_score": 60,
  "notify_each": true
}
```

Supported free-provider categories currently include hotels, restaurants, travel agencies, real-estate agencies, builders, hairdressers, gyms, clinics, dentists, veterinary practices, pharmacies and cafes. More discovery providers can be added later.

## Run the agent across multiple markets

`POST /api/agent/run`

```json
{
  "industries": [
    "hoteles",
    "agencias de viajes",
    "inmobiliarias"
  ],
  "cities": [
    "Buenos Aires",
    "Córdoba",
    "Rosario"
  ],
  "country": "Argentina",
  "leads_per_search": 5,
  "minimum_score": 60,
  "notify_each": true
}
```

This runs every industry/city combination, skips duplicate leads already present in MySQL, analyzes companies with or without websites, stores successful analyses and sends email notifications.

If MySQL is not configured yet, discovery and AI analysis can still proceed, but each affected result will report a database error and `stored` will remain `false`.

## Database

Create the initial schema with `database/schema.sql` and set the real `DATABASE_URL` in `backend/.env`.

## Outreach policy

The agent prepares targeted outreach drafts but does not automatically contact discovered businesses. Human approval remains part of the outreach step so the system is used for relevant prospecting rather than bulk unsolicited messaging.
