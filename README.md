NourishStrong
NourishStrong is a React-based single-page application (SPA) designed for nutrition and mood tracking with built-in coaching features. It leverages modern web technologies and role-based user management to deliver a responsive and scalable wellness platform.

Core Technologies
Frontend Framework: React 18, using functional components and hooks for state management.

Routing & Navigation: Simple client-side navigation handled via React state with role-specific menus.

Build Tools: Uses react-scripts from Create React App for easy project scaffolding, development, and production builds.

Styling: Inline styles combined with CSS for component-level styling.

Deployment: Hosted on GitHub Pages using the gh-pages branch and automated deployment workflows.

Features & Implementation
Meal Photo Upload: Users upload photos with descriptions and select hunger and satisfaction ratings.

Mood Tracker with Journaling: Rich text input areas for users to log moods alongside quantitative ratings.

Barcode Scanner: Integrates device camera access or input to scan product barcodes; fetches nutrition data from third-party nutrition APIs using RESTful calls.

Role-Based Access Control: Two roles—clients and coaches—control visibility and feature access. Clients get nutrition and mood tools, while coaches have dashboards summarizing client data and communication tools.

User Profiles: User data and images stored and managed in state with future plans for persistent backend integration.

Authentication: A mock authentication component manages simple sign-up/login flows with password strength validation, role selection, and in-app session state.

Testing & CI: Unit and integration tests run on multiple Node.js versions via GitHub Actions ensuring compatibility and quality.

Continuous Deployment: Automated CI/CD pipelines using GitHub Actions build, test, and deploy updates, streamlining development workflows.

Development Setup
Node.js: Version 22.x recommended (specified in package.json engines).

NPM Scripts:

npm start — Launches development server with hot reload.

npm run build — Creates optimized production build.

npm run deploy — Publishes build to GitHub Pages.

Local Testing: Supports component-level testing and local development with immediate feedback.
