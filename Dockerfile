FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /code

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collected at build time so the image is self-contained. DEBUG/SECRET_KEY are
# supplied so settings can import without the real production secrets ever
# entering the image.
RUN DEBUG=True SECRET_KEY=build-only python manage.py collectstatic --noinput

# Do not run as root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

CMD ["./start.sh"]
