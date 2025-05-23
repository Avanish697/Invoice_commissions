FROM python:3.11-slim

# Install required system packages for pyodbc and SQL Server
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    gnupg2 \
    curl \
    unixodbc \
    unixodbc-dev \
    libpq-dev \
    freetds-dev \
    freetds-bin \
    tdsodbc

# ✅ Install Microsoft ODBC Driver 17 for SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql17 && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Expose port 8080 for Render
EXPOSE 8080

# ✅ Updated to point to the correct WSGI callable: "server" in main.py
CMD ["gunicorn", "-b", ":8080", "main:server"]
