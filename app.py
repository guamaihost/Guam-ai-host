if _name_ == "_main_": import os

    seed()

    host = "0.0.0.0"

    port = int(os.environ.get("PORT", "8000"))

    print(f"Guam AI Host V4 running on {host}:{port}")

    ThreadingHTTPServer((host, port), Handler).serve_forever()
