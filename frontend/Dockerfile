# Build the frontend assets
FROM node:20-alpine AS build

# Set working directory inside the container
WORKDIR /app

# Copy dependency files first to take advantage of Docker layer caching
COPY package*.json ./

# Install dependencies (change to pnpm/yarn if needed)
RUN npm install 

# Copy the rest of the frontend source code
COPY . .

# Build the production-ready static files (Vite/CRA typically use this command)
RUN npm run build

# Serve the built static assets using Nginx
FROM nginx:1.27-alpine



# Copy built frontend files from the build stage to Nginx's static directory
COPY --from=build /app/dist /usr/share/nginx/html

# ⭐️ 新增：覆盖 Nginx 默认配置（SPA 必须）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80 inside the container (map to 5173/8080 externally if preferred)
EXPOSE 80

# Run Nginx in the foreground (required for Docker containers)
CMD ["nginx", "-g", "daemon off;"]
