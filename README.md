# VisitationBook API

A Django REST API for managing digital visitation books, obituaries, and guest information for funeral homes.

## Features

- User authentication and authorization using JWT tokens
- Digital visitation book management
- Obituary creation and management
- Guest information collection and management
- Payment processing integration with Stripe
- Email notifications system
- Visit counter for books and obituaries
- File management for images and PDFs
- Admin interface for data management

## Tech Stack

- Django 
- Django REST Framework
- PostgreSQL
- Redis
- Nginx
- Docker
- Stripe API
- JWT Authentication

## Prerequisites

- Docker and Docker Compose
- Make
- Python 3.8+
- PostgreSQL
- Redis
- Stripe account for payment processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/BosterJack/VisitationBook_Backend.git
cd visitationbook-backend
```

2. Configure your environment variables:
The environment variables are stored in `.env/.env` in the same directory as `docker-compose.yml`. Make sure to set up all required variables before starting the application.

3. Build and start the Docker containers using Make:
```bash
# Build the containers
make build

# Start the services
make run
```

## Available Make Commands

### Management Commands
```bash
make build         # Build the backend
make run          # Start backend services in detached mode
make down         # Remove backend services
make stop         # Stop backend services
make start        # Start backend services
make restart      # Restart backend services
make ps           # List running processes
make update       # Update web container
```

### Shell Access
```bash
make shellweb     # Connect to the web server
make shelldb      # Connect to the database server
make psql         # Access the PostgreSQL database
make shellnginx   # Connect to the nginx server
```

### Database Operations
```bash
make dumpall      # Export the entire database
make dumptable    # Export specific tables
make copymigrations # Copy migrations from container
make copyweb      # Sync web container files locally
```

### Django Commands
```bash
make migrations    # Create database migrations
make migrate      # Apply database migrations
make collectstatic # Generate static assets
```

### Logs
```bash
make logweb       # Display web server logs
make logdb        # Display database server logs
```

### SSL Certificate
```bash
make generatesslnginx  # Generate SSL certificates for domains
```

## API Endpoints

### Authentication
- `POST /api/login/` - User login
- `POST /api/token/refresh/` - Refresh JWT token

### Users
- `GET /api/users/` - List users
- `PUT /api/users/<id>/` - Update user information
- `GET /api/users/<id>/` - Get user details

### Books
- `GET /api/books/` - List available books
- `GET /api/books/<id>/` - Get book details

### Book Purchases
- `GET /api/book-purchases/` - List user's book purchases
- `POST /api/book-purchases/` - Create new book purchase
- `GET /api/book-purchases/<id>/` - Get book purchase details
- `PUT /api/book-purchases/<id>/` - Update book purchase
- `POST /api/book-purchases/<id>/process-payment/` - Process payment
- `POST /api/book-purchases/<id>/increment-visit/` - Increment visit counter

### Guest Information
- `GET /api/guest-infos/` - List guest information
- `POST /api/guest-infos/` - Add guest information
- `PUT /api/guest-infos/<id>/` - Update guest information

### Payments
- `GET /api/payment-methods/` - List payment methods
- `POST /api/payment-methods/` - Add payment method
- `GET /api/payment-transactions/` - List payment transactions

### Obituaries
- `GET /api/obituaries/` - List obituaries
- `POST /api/obituaries/` - Create obituary
- `PUT /api/obituaries/<id>/` - Update obituary
- `POST /api/obituaries/<id>/increment-visit/` - Increment visit counter

### Email
- `POST /api/emails/` - Send thank you emails to guests

## File Structure

```
visitationbook-backend/
├── visitationbookapi/
│   ├── models/
│   ├── serializers/
│   ├── viewsets/
│   ├── permissions/
│   └── utils/
├── .env/
│   ├── nginx/
│   ├── pg/
│   ├── python/
│   ├── .env
│   └── docker-compose.yml
└── Makefile
```

## Environment Variables

Key environment variables needed in `.env/.env`:
- `DEBUG`
- `SECRET_KEY`
- `POSTGRES_*` (database configuration)
- `STRIPE_*` (Stripe API keys)
- `EMAIL_*` (email configuration)
- `REDIS_*` (Redis configuration)

## Development

1. Run migrations:
```bash
make migrate
```

2. Create a superuser:
```bash
docker-compose exec visitationbook_web python manage.py createsuperuser
```

3. Access the admin interface at `http://localhost:8000/admin/`

## Production Deployment

The project includes Docker configurations for production deployment with:
- Nginx as reverse proxy
- PostgreSQL for database
- Redis for caching
- Let's Encrypt SSL certificates
- Static and media file serving

## Security Features

- JWT authentication
- Permission-based access control
- Secure file uploads
- Payment information encryption
- CORS protection
- SSL/TLS encryption

## Author

Jacques SOUDE <bostersoude@gmail.com>

## License

[License Information]