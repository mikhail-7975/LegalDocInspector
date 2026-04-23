FROM python:3.12-slim-bookworm

WORKDIR /app

COPY services/bff-orchestrator/requirements.txt /app/requirements-bff.txt
RUN pip install --no-cache-dir -r /app/requirements-bff.txt

# Optional: full legacy OCR/PDF stack — uncomment next line and ensure requirements.txt exists at repo root
# COPY requirements.txt /workspace-req.txt
# RUN pip install --no-cache-dir -r /workspace-req.txt

COPY services/bff-orchestrator/src /app/src

ENV PYTHONPATH=/app/src:/workspace
ENV LEGACY_REPO_ROOT=/workspace

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
