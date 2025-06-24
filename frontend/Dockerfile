FROM node:20-alpine AS builder
WORKDIR /app

# Устанавливаем зависимости --omit=dev
COPY package*.json ./
RUN npm install 

# Копируем исходники и собираем приложение
COPY . .
RUN npm run build

# --- Production image ---
FROM nginx:alpine

# Копируем собранную статику
COPY --from=builder /app/dist /usr/share/nginx/html

# Копируем кастомный конфиг nginx (если он существует)
# Предусматриваем, что в корне проекта есть каталог nginx с конфигом
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"] 