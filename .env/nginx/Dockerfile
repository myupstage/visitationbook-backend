FROM nginx:1.19.0-alpine
LABEL maintainer="Jacques SOUDE <bostersoude@gmail.com>"

RUN apk add --no-cache bash certbot certbot-nginx

COPY .env/nginx/default.conf /etc/nginx/conf.d

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]