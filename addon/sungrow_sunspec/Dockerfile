FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
COPY app/ /app/
COPY profiles/ /app/profiles/
COPY run.sh /run.sh
RUN apk add --no-cache su-exec \
    && chmod a+x /run.sh \
    && addgroup -S app \
    && adduser -S -G app app

CMD ["/run.sh"]
