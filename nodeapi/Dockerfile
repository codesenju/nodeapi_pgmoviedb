#FROM docker.io/node
FROM docker.io/node:lts-alpine
# Create app directory
WORKDIR /usr/src/app

# Install app dependencies
# A wildcard is used to ensure both package.json AND package-lock.json are copied
# where available (npm@5+)
COPY package*.json ./

# Install bind-tools
RUN apk upgrade && \
    apk add bind-tools && \
    apk add postgresql-client && \
    apk add stress-ng

RUN npm install
# If you are building your code for production
# RUN npm ci --only=production

# Bundle app source
COPY . .

EXPOSE 3000
CMD [ "node", "server.js" ]