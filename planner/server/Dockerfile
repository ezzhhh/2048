FROM python:3.12-slim
WORKDIR /app
COPY planner /app/planner
RUN pip install --no-cache-dir -r /app/planner/server/requirements.txt
ENV PLANER_DATA=/data/planer.sqlite
EXPOSE 8787
CMD ["uvicorn", "planner.server.app:app", "--host", "0.0.0.0", "--port", "8787"]
