FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY index.html styles.css app.js /usr/share/nginx/html/

COPY joy-ai-upgrade.js joy-ai-upgrade.css joy-ai-avatar.png /usr/share/nginx/html/

COPY community-tooltip-fix.js /usr/share/nginx/html/

COPY joy-auth.js /usr/share/nginx/html/
EXPOSE 80
