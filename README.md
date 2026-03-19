# Khullaerp

Khullaerp is a modern, responsive, multi-tenant Enterprise Resource Planning system built with Django. It provides comprehensive tools tailored for businesses in Nepal, including financial accounting, voucher management, human resources, inventory tracking, and sales operations.

## Features

- **Multi-Tenancy**: Built using `django-tenants` for true data isolation across different business clients.
- **Financial Accounting**: Robust Chart of Accounts (COA), Journal entries, Receipts, Payments, Contra, and Sales/Purchase tracking with subledgers.
- **Reporting**: Trial Balance, Profit & Loss, Balance Sheet, Cash Flow, VAT Reports, and TDS Tracking.
- **Human Resources (HR)**: Employee management and payroll processing.
- **Sales & Purchases**: Invoice generation, purchase bills, and vendor/customer management.
- **Taxation Compliance**: Built-in support for Value Added Tax (VAT) and Tax Deducted at Source (TDS) specifically formatted for regional requirements.
- **Modern UI**: Polished, mobile-responsive user interface crafted with Bootstrap 5, Alpine.js, and custom aesthetics.
- **Asynchronous Tasks**: Background task processing handled via Celery.

## Tech Stack

- **Backend**: Django 6.x, Python
- **Database**: PostgreSQL (Required for `django-tenants` schema support)
- **Frontend**: HTML5, CSS3, Bootstrap 5, Alpine.js, TomSelect
- **Task Queue**: Celery (with Redis or pure DB polling via Django-Celery-Results)
- **PDF Generation**: ReportLab

## Pre-requisites

- Python 3.10+
- PostgreSQL server (Ensure the PostgreSQL user has rights to create databases and schemas)
- (Optional) Redis for Celery message brokering

## Installation and Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/khullaerp.git
   cd khullaerp
   ```

2. **Set up a Virtual Environment:**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Copy the example environment file and update it with your own database credentials and secret key.
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` to include your PostgreSQL credentials (`DB_USER`, `DB_PASSWORD`, `DB_NAME`).*

5. **Initialize Database and Schemas:**
   Since this project uses `django-tenants`, you must run the specific tenant migrations to create the "public" schema and base structures.
   ```bash
   python manage.py migrate_schemas --shared
   python manage.py migrate_schemas --tenant
   ```
   *(Alternatively, run the custom setup script `python create_db.py` if configured).*

6. **Create a Superuser (on the public schema):**
   ```bash
   python manage.py create_tenant_superuser
   ```

7. **Run the Development Server:**
   ```bash
   python manage.py runserver
   ```
   Access the system at `http://localhost:8000`.

## Contributing

Contributions, issues, and feature requests are welcome!

## License

This project is licensed under the [MIT License](LICENSE).
