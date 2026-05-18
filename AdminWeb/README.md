
# AdminWeb

AdminWeb is the administrative web interface for TOOL-E, providing staff with authenticated access to inventory management, transaction monitoring, manual fallback workflows, analytics, reporting, and ML tool-identification debugging.

## Features

- **Inventory Management**: Add, search, and manage tool catalog.
- **Transaction Monitoring**: View, filter, and manage borrow/return records.
- **Manual Transactions**: Fallback checkout/return for edge cases.
- **Analytics Dashboard**: Live stats, period analytics, and top tools chart.
- **Reports**: Date-range transaction export (CSV).
- **ML Debug**: Upload images to test tool-identification model.

## Tech Stack

- React 19 + TypeScript
- Vite
- React Router
- TanStack React Query
- Zustand (persisted auth store)
- Axios
- Tailwind CSS
- Recharts
- Lucide React

## Getting Started

### Prerequisites

- Node.js 20+
- npm 10+
- Running backend API (see ../Server)

### Setup

1. Clone the repo and navigate to `AdminWeb`.
2. Create a `.env` file with:
   ```
   VITE_API_BASE_URL=<API_ADDRESS>
   VITE_AUTH_TOKEN_TTL_SECONDS=<DESIRED_TOKEN_EXPIRY_TIME_IN_SECONDS> (default: 8 hours)
   ```
3. Install dependencies:
   ```
   npm install
   ```
4. Start the development server:
   ```
   npm run dev
   ```
5. Open the URL printed by Vite (default: http://localhost:5173).

### Scripts

- `npm run dev` — Start development server
- `npm run build` — Build for production (includes type-check)
- `npm run preview` — Preview production build locally
- `npm run lint` — Lint codebase

## Project Structure

- `src/App.tsx` — App routes and navigation
- `src/components/layout/DashboardLayout.tsx` — Auth-protected layout, sidebar, sync, user info
- `src/lib/axios.ts` — Axios client with API base URL and auth token
- `src/lib/react-query.ts` — React Query client config
- `src/lib/authStore.ts` — Zustand auth store (persisted)
- `src/features/` — Feature pages:
  - `auth/` — Login
  - `dashboard/` — Analytics dashboard
  - `inventory/` — Tool catalog
  - `transactions/` — Borrow/return records
  - `manual-transaction/` — Manual checkout/return
  - `reports/` — Reports and export
  - `debug/` — ML tool-identification

## Routing

- `/login` — Login page (redirects if authenticated)
- `/dashboard` — Main dashboard (protected)
- `/inventory` — Inventory management (protected)
- `/transactions` — Transactions log (protected)
- `/manual-transaction` — Manual checkout/return (protected)
- `/reports` — Reports and export (protected)
- `/debug-ml` — ML debug (protected)

Unauthenticated users are always redirected to `/login`.

## Authentication & Data

- Auth state is persisted in browser storage (Zustand)
- All API requests use the token (via axios interceptor)
- "Sync Data" in sidebar refetches all active queries

## Development Notes

- Tailwind config: see `tailwind.config.js`
- Vite config: see `vite.config.ts` (network access enabled)
- TypeScript strict mode enabled
- Linting: ESLint with React/TypeScript plugins

## Limitations / TODO

- **Role-based permissions are not yet implemented:**
   - All authenticated users have the same level of access in AdminWeb. There is currently no distinction between admin, staff, or other roles.

- **Manual transactions on the website cannot fully replicate kiosk transactions:**
   - The kiosk captures and uploads images of tools for both ML identification and record-keeping. These images are stored on the server drive.
   - Manual transactions performed via the AdminWeb interface do **not** capture or upload tool images.
   - As a result, tool images will only be accessible from the website if:
      - The server is deployed and has access to persistent storage, **or**
      - The school or admin decides to upload images to the database (e.g., images taken during ML processing at the kiosk).
   - If neither of these conditions is met, tool images will not be accessible from the website for those transactions.

# License

See [../LICENSE](../LICENSE)
