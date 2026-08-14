FROM node:20-alpine

WORKDIR /app

# Copy dependency files
COPY package*.json ./

# Install packages
RUN npm install

# Copy source code
COPY . .

EXPOSE 5173

# Run development server binding to all network interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
