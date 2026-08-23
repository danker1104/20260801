FROM nginx:1.27-alpine

# Nginx template is rendered at container startup using environment variables.
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY . /usr/share/nginx/html

EXPOSE 80
