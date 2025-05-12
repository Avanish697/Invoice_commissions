# Use a slim Python image
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y gnupg curl unixodbc-dev gcc g++ && \
    curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y msodbcsql17

# Set working directory
WORKDIR /app

# Copy all files to container
COPY . .

# Install Python dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Run your app
CMD ["python", "main.py"]
