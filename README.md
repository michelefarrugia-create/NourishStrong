NourishStrong
NourishStrong is a React-based nutrition and mood tracking application designed with coaching support features to help users develop mindful eating and wellness habits.

Features

Upload meal photos with descriptions, hunger ratings, and satisfaction levels.

Mood tracking with journaling options.

Barcode scanner integrating with nutrition APIs for easy food logging.

Role-based access control to differentiate clients and coaches.

User profiles with editable pictures.

A support dashboard for coaches to gain insights and track client progress.

Getting Started

Prerequisites

Node.js (version 18.x recommended)

npm (comes with Node.js)

Running Locally
Clone the repository:
git clone https://github.com/michelefarrugia-create/NourishStrong.git
cd NourishStrong

Install dependencies:
npm install

Start the development server:
npm start

Open your browser and navigate to http://localhost:3000 to use the app locally.

Building for Production
To create a production-ready build, run:
npm run build
The optimized build will be in the build folder.

Deployment
The app is deployed on GitHub Pages via the gh-pages branch.

To deploy manually:
npm run deploy

This runs the build and publishes the contents of the build folder to the gh-pages branch.

Visit your live app at:
https://michelefarrugia-create.github.io/NourishStrong/

Project Structure

public/ — Public static files including the main index.html.

src/ — React application source code.

package.json — NPM package and script configuration.

Troubleshooting

Ensure public/index.html exists as it’s essential for building React apps.

Run npm run build locally to catch build errors before deploying.

Check environment variables if your app integrates with external APIs.

Contributing
Feel free to fork and submit pull requests or raise issues for discussion.
