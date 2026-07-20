
Install the package in editable mode:
```
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Prepare Django server with HTTP:
```
mkcert -install
mkcert -cert-file tls\server.crt -key-file tls\server.key localhost 127.0.0.1 ::1
```

Verify Djjango:
```
.\.venv\Scripts\python.exe web\manage.py check
```

Start Django server:
```
.\.venv\Scripts\python.exe -m uvicorn config.asgi:application --app-dir web --host 127.0.0.1 --port 8000 --ssl-certfile tls\server.crt --ssl-keyfile tls\server.key
```

