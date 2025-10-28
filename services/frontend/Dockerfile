# Multi-stage build for frontend
FROM nginx:1.25-alpine

# Create non-root user
RUN addgroup -g 1000 frontend && \
    adduser -D -u 1000 -G frontend frontend && \
    chown -R frontend:frontend /var/cache/nginx && \
    chown -R frontend:frontend /var/log/nginx && \
    chown -R frontend:frontend /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown -R frontend:frontend /var/run/nginx.pid

# Remove default nginx config and copy custom configuration
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Copy frontend files
COPY login.html /usr/share/nginx/html/login.html
COPY app.html /usr/share/nginx/html/app.html
COPY index.html /usr/share/nginx/html/index.html
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/

# Set ownership
RUN chown -R frontend:frontend /usr/share/nginx/html

# Switch to non-root user
USER frontend

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
