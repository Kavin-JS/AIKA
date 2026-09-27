FROM node:20-slim

WORKDIR /app

# Copy the lockfile too and use `npm ci`, so the image installs the
# exact versions CI validates rather than letting `npm install` resolve
# (and potentially drift) dependencies fresh inside the container.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]
