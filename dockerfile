FROM huggingface/transformers-pytorch-gpu:latest  
ENV TRANSFORMERS_CACHE=/app/huggingface
COPY huggingface /app/huggingface

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --assume-yes git poppler-utils tesseract-ocr-rus

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "run.py"]