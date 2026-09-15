from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from database import get_db_connection
from schemas import UserCreate, UserLogin
from ticket_schemas import TicketCreate
from security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)


app = FastAPI(title="Helpdesk Ticket Management System")


# =========================
# JWT SECURITY
# =========================

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = decode_access_token(token)

        user_id = payload.get("user_id")
        email = payload.get("email")
        role = payload.get("role")

        if user_id is None or email is None or role is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication token"
            )

        return {
            "user_id": user_id,
            "email": email,
            "role": role
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )



def require_role(*allowed_roles):
    def role_checker(
        current_user: dict = Depends(get_current_user)
    ):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail="You do not have permission to perform this action"
            )

        return current_user

    return role_checker


# =========================
# HOME
# =========================

@app.get("/")
def home():
    return {
        "message": "Helpdesk Ticket Management System API is running"
    }


# =========================
# HEALTH CHECK
# =========================

@app.get("/health")
def health_check():
    connection = get_db_connection()

    if connection.is_connected():
        connection.close()
        return {
            "status": "healthy",
            "database": "connected"
        }

    return {
        "status": "unhealthy",
        "database": "disconnected"
    }


# =========================
# CREATE USER
# =========================

@app.post("/users")
def create_user(user: UserCreate):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        query = """
            INSERT INTO users (name, email, password, role)
            VALUES (%s, %s, %s, %s)
        """

        hashed_password = hash_password(user.password)

        values = (
            user.name,
            user.email,
            hashed_password,
            user.role
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "message": "User created successfully",
            "user_id": cursor.lastrowid
        }

    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# LOGIN API + JWT
# =========================

@app.post("/login")
def login_user(user: UserLogin):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT id, name, email, password, role
            FROM users
            WHERE email = %s
        """

        cursor.execute(query, (user.email,))
        db_user = cursor.fetchone()

        if db_user is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        if not verify_password(
            user.password,
            db_user["password"]
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password"
            )

        access_token = create_access_token(
            {
                "user_id": db_user["id"],
                "email": db_user["email"],
                "role": db_user["role"]
            }
        )

        return {
            "message": "Login successful",
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": db_user["id"],
            "name": db_user["name"],
            "email": db_user["email"],
            "role": db_user["role"]
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# CREATE TICKET
# =========================

@app.post("/tickets")
def create_ticket(
    ticket: TicketCreate,
    current_user: dict = Depends(
        require_role("USER", "AGENT", "ADMIN")
    )
):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        check_query = """
            SELECT id
            FROM users
            WHERE id = %s
        """

        cursor.execute(
            check_query,
            (current_user["user_id"],)
        )
        user = cursor.fetchone()

        if user is None:
            raise HTTPException(
                status_code=404,
                detail="Authenticated user not found"
            )

        query = """
            INSERT INTO tickets
            (title, description, priority, category, created_by)
            VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            ticket.title,
            ticket.description,
            ticket.priority,
            ticket.category,
            current_user["user_id"]
        )

        cursor.execute(query, values)
        connection.commit()

        return {
            "message": "Ticket created successfully",
            "ticket_id": cursor.lastrowid
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# GET ALL TICKETS - PROTECTED
# =========================

@app.get("/tickets")
def get_tickets(
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    assigned_to: int | None = None,
    search: str | None = None,
    current_user: dict = Depends(
        require_role("USER", "AGENT", "ADMIN")
    )
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                id,
                title,
                description,
                priority,
                status,
                category,
                created_by,
                assigned_to,
                created_at,
                updated_at
            FROM tickets
            WHERE 1 = 1
        """

        params = []

        if status:
            status = status.upper()
            valid_statuses = [
                "OPEN",
                "IN_PROGRESS",
                "RESOLVED",
                "CLOSED"
            ]

            if status not in valid_statuses:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid status"
                )

            query += " AND status = %s"
            params.append(status)

        if priority:
            priority = priority.upper()
            valid_priorities = [
                "LOW",
                "MEDIUM",
                "HIGH",
                "CRITICAL"
            ]

            if priority not in valid_priorities:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid priority"
                )

            query += " AND priority = %s"
            params.append(priority)

        if category:
            query += " AND category = %s"
            params.append(category)

        if assigned_to is not None:
            query += " AND assigned_to = %s"
            params.append(assigned_to)

        if search:
            query += """
                AND (
                    title LIKE %s
                    OR description LIKE %s
                )
            """
            search_value = f"%{search}%"
            params.extend([search_value, search_value])

        query += " ORDER BY created_at DESC"

        cursor.execute(query, tuple(params))
        tickets = cursor.fetchall()

        return {
            "count": len(tickets),
            "tickets": tickets
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# GET SINGLE TICKET
# =========================

@app.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: int,
    current_user: dict = Depends(
        require_role("USER", "AGENT", "ADMIN")
    )
):

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        query = """
            SELECT
                id,
                title,
                description,
                priority,
                status,
                category,
                created_by,
                assigned_to,
                created_at,
                updated_at
            FROM tickets
            WHERE id = %s
        """

        cursor.execute(query, (ticket_id,))
        ticket = cursor.fetchone()

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        return ticket

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# ASSIGN TICKET TO AGENT
# =========================

@app.put("/tickets/{ticket_id}/assign")
def assign_ticket(
    ticket_id: int,
    agent_id: int,
    current_user: dict = Depends(
        require_role("ADMIN")
    )
):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # Check whether the ticket exists
        cursor.execute(
            "SELECT id FROM tickets WHERE id = %s",
            (ticket_id,)
        )
        ticket = cursor.fetchone()

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        # Check whether the selected user exists and is an AGENT
        cursor.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE id = %s
            """,
            (agent_id,)
        )
        agent = cursor.fetchone()

        if agent is None:
            raise HTTPException(
                status_code=404,
                detail="Agent not found"
            )

        if agent["role"] != "AGENT":
            raise HTTPException(
                status_code=400,
                detail="Selected user is not an AGENT"
            )

        # Assign ticket to the agent
        cursor.execute(
            """
            UPDATE tickets
            SET assigned_to = %s
            WHERE id = %s
            """,
            (agent_id, ticket_id)
        )

        connection.commit()

        return {
            "message": "Ticket assigned successfully",
            "ticket_id": ticket_id,
            "assigned_to": agent_id,
            "agent_name": agent["name"]
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# UPDATE TICKET STATUS
# =========================

@app.put("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status: str,
    current_user: dict = Depends(
        require_role("AGENT", "ADMIN")
    )
):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        check_query = """
            SELECT id
            FROM tickets
            WHERE id = %s
        """

        cursor.execute(check_query, (ticket_id,))
        ticket = cursor.fetchone()

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        valid_statuses = [
            "OPEN",
            "IN_PROGRESS",
            "RESOLVED",
            "CLOSED"
        ]

        status = status.upper()

        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid status"
            )

        query = """
            UPDATE tickets
            SET status = %s
            WHERE id = %s
        """

        cursor.execute(query, (status, ticket_id))
        connection.commit()

        return {
            "message": "Ticket status updated successfully",
            "ticket_id": ticket_id,
            "status": status
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()


# =========================
# DELETE TICKET
# =========================

@app.delete("/tickets/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    current_user: dict = Depends(
        require_role("ADMIN")
    )
):

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        check_query = """
            SELECT id
            FROM tickets
            WHERE id = %s
        """

        cursor.execute(check_query, (ticket_id,))
        ticket = cursor.fetchone()

        if ticket is None:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found"
            )

        query = """
            DELETE FROM tickets
            WHERE id = %s
        """

        cursor.execute(query, (ticket_id,))
        connection.commit()

        return {
            "message": "Ticket deleted successfully",
            "ticket_id": ticket_id
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as e:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
        connection.close()