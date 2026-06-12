# How to Run?

1. 
    ```
    docker compose up -d
    ```
.\venv\Scripts\activate
python manage.py set_webhook https://swab-regretful-duo.ngrok-free.dev/api/v1/telegram/webhook/

2. 
    ```
    .\venv\Scripts\activate
    python manage.py runserver
    ```

3. 
    ```
    .\venv\Scripts\activate
    celery -A quiz_backend worker -l INFO --pool=solo
    ```

4. 
    ```
    .\venv\Scripts\activate
    python manage.py telegram_polling
    ```