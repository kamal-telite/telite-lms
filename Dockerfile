FROM moodlehq/moodle-php-apache:8.1

LABEL org.opencontainers.image.source="https://github.com/YOUR_GITHUB_USERNAME/telite-lms"
LABEL org.opencontainers.image.description="Telite LMS Moodle image with PostgreSQL support"
LABEL org.opencontainers.image.licenses="GPL-3.0"

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev \
    && docker-php-ext-install pgsql \
    && rm -rf /var/lib/apt/lists/*

COPY moodle/ /var/www/html/
COPY docker-config.php /var/www/html/config.php

RUN mkdir -p /var/www/moodledata \
    && chown -R www-data:www-data /var/www/html /var/www/moodledata \
    && chmod -R 0755 /var/www/html \
    && chmod -R 0777 /var/www/moodledata

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

CMD ["apache2-foreground"]
