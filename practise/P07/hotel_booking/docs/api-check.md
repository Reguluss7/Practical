# API & PostgreSQL Persistence Check (7 Requests)

Run with `python main.py` listening on `http://localhost:5080`.

1. **Search free rooms (`200 OK`)** — returns `R7`, `R8`, `R9`:
   ```powershell
   curl.exe -i "http://localhost:5080/rooms/available?check_in=2026-12-01&check_out=2026-12-04&limit=10"