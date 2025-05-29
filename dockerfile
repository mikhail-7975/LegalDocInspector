FROM python:3.10

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --assume-yes git poppler-utils tesseract-ocr-rus


WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "run.py"]