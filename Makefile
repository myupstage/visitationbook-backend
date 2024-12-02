# Date 16/07/2024
# @uthor: Jacques SOUDE <bostersoude@gmail.com>
# Useful production commands with makefile

compose_path = .env/docker-compose.yml

### MANAGEMENT COMMAND
# Build the backend
build:
	@docker-compose -f $(compose_path) build

# Start backend services
run:
	@docker-compose -f $(compose_path) up -d

# Remove backend services
down:
	@docker-compose -f $(compose_path) down

# Stop backend services
stop:
	@docker-compose -f $(compose_path) stop

# Start backend services
start:
	@docker-compose -f $(compose_path) start

# Restart backend services
restart:
	@docker-compose -f $(compose_path) stop && docker-compose -f $(compose_path) start

# List running processes
ps:
	@docker container ps

update:
	@docker container exec visitationbook_web sh .prod/python/update.sh

#### SHELL IN CONTAINERS
# Connect to the web server
shellweb:
	@docker container exec -ti visitationbook_web sh

# 
shelldb:
	@docker container exec -ti visitationbook_db sh

# Access the database
psql:
	@docker container exec -ti visitationbook_db psql -U visitationbook


##### Database backup
# Export the entire database.
dumpall:
	@docker exec -t visitationbook_db pg_dumpall -c -U visitationbook > visitationbook_`date +%d-%m-%Y"_"%H_%M_%S`.sql

dumptable:
	@docker exec -t visitationbook_db pg_dump -U visitationbook -d visitationbook -t django_migrations > django_migrations.sql

copymigrations:
	@docker cp visitationbook_web:/home/app/web/visitationbookapi/migrations/ visitationbookapi/

copyweb:
	@docker container exec visitationbook_web rsync -av --update /home/app/web/ .

#### DJANGO COMMANDS
# Create database migrations
migrations:
	@docker container exec -ti visitationbook_web python manage.py makemigrations

# Apply database migrations
migrate:
	@docker container exec -ti visitationbook_web python manage.py migrate

# Generate static assets
collectstatic:
	@docker container exec -ti visitationbook_web python manage.py collectstatic --noinput --clear

# Display web server logs
logweb:
	@docker container logs --follow visitationbook_web

# Display database server logs
logdb:
	@docker container logs --follow visitationbook_db

shellnginx:
	@docker container exec -ti visitationbook_nginx sh

generatesslnginx:
	@certbot --nginx -d backend.visitationbook.com -d account.visitationbook.com -d pgadmin.visitationbook.com