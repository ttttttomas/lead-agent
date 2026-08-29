# Lead Agent

AI-powered lead generation and qualification agent for software agencies.

## Objective

Lead Agent finds potential clients, analyzes their public web presence, scores opportunities, recommends the most relevant software service, and prepares personalized outreach messages for human approval.

## Stack

- Frontend: Next.js + Tailwind CSS
- Backend: FastAPI
- Database: MySQL
- AI: Kimi K3 via NVIDIA API

## MVP flow

1. Discover public business leads.
2. Collect public company and website data.
3. Analyze the website and business context.
4. Send structured context to Kimi K3.
5. Generate a 0-100 opportunity score, detected problems, and recommended service.
6. Save the lead in the CRM.
7. Generate a personalized outreach draft.
8. Human reviews and approves before contact.

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

Never commit real API keys.

Backend:

```env
NVIDIA_API_KEY=
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/lead_agent
```

Frontend:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Planned API

- `GET /health`
- `GET /api/leads`
- `POST /api/leads`
- `POST /api/leads/{id}/analyze`
- `POST /api/leads/{id}/outreach`

## Outreach policy

The MVP uses human approval before sending outreach. It is designed for targeted, relevant prospecting rather than bulk unsolicited messaging.
