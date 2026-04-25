FROM python:3.12

COPY requirements.txt /app/
WORKDIR /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80
ENTRYPOINT ["python", "main.py", "80"]
