PWA / home-screen icons (full MTE logo on light #F5F5F5 canvas):

  - icon-192x192.png
  - icon-512x512.png

Generated from assets/mte_logo.png. Served at /icons/* via IIS (web.config).

Browser tab / bookmark icons live in frontend/public/ (copied into dist on build):
  - favicon.ico
  - favicon-32x32.png
  - apple-touch-icon.png

Regenerate after a logo change (requires Pillow):

  python deploy/generate_site_icons.py

Then rebuild the frontend: deploy\build_frontend.bat
