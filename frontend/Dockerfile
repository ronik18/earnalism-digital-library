FROM node:20-alpine AS build

WORKDIR /app

ARG REACT_APP_BACKEND_URL=https://api.theearnalism.com
ARG REACT_APP_API_URL=https://api.theearnalism.com
ARG REACT_APP_GOOGLE_CLIENT_ID=
ARG REACT_APP_POSTHOG_KEY=
ARG REACT_APP_POSTHOG_HOST=https://us.i.posthog.com

ENV REACT_APP_BACKEND_URL=$REACT_APP_BACKEND_URL \
    REACT_APP_API_URL=$REACT_APP_API_URL \
    REACT_APP_GOOGLE_CLIENT_ID=$REACT_APP_GOOGLE_CLIENT_ID \
    REACT_APP_POSTHOG_KEY=$REACT_APP_POSTHOG_KEY \
    REACT_APP_POSTHOG_HOST=$REACT_APP_POSTHOG_HOST

COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
