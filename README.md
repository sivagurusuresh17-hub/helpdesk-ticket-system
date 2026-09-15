# Helpdesk Ticket Management System

A backend REST API for managing helpdesk support tickets with authentication, role-based authorization, ticket assignment, search, filtering, and automated testing.

## 🚀 Features

- User registration
- Secure password hashing using Argon2
- JWT-based authentication
- Role-based authorization
- User roles:
  - USER
  - AGENT
  - ADMIN
- Create and manage support tickets
- Ticket status management
- Ticket priority management
- Admin-only ticket assignment
- Search tickets by title and description
- Filter tickets by:
  - Status
  - Priority
  - Category
  - Assigned agent
- MySQL database integration
- Input validation using Pydantic
- Exception handling
- Automated API testing using Pytest
- Environment-based configuration using `.env`

## 🛠️ Tech Stack

### Backend
- Python
- FastAPI
- JWT
- Argon2

### Database
- MySQL

### Testing
- Pytest
- FastAPI TestClient
- HTTPX

### Tools
- Git
- GitHub
- VS Code

## 🔐 Authentication

The application uses JWT-based authentication.

After successful login, the API returns an access token.

The token is used to access protected endpoints.

Example:

```text
Authorization: Bearer <access_token>