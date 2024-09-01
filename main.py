import mysql.connector
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origin = [
    "http://localhost:4200",
]

# Add the CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origin,  # List the frontend's origin here
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)


# MySQL database connection
def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",  # Update with your MySQL host
        user="root",  # Update with your MySQL username
        password="root",  # Update with your MySQL password
        database="train_booking"
    )
    return connection


class BookingRequest(BaseModel):
    number_of_seats: int


class BookingResponse(BaseModel):
    booked_seats: List[int]


@app.get("/")
def read_root():
    return {"message": "Hello from Koyeb"}


@app.get("/seats")
def get_seats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM seats")
    seats = cursor.fetchall()
    cursor.close()
    conn.close()
    return seats


@app.post("/book", response_model=BookingResponse)
def book_seats(booking: BookingRequest):
    if booking.number_of_seats > 7:
        raise HTTPException(status_code=400, detail="Cannot book more than 7 seats at a time")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM seats WHERE status = 'available'")
    available_seats = cursor.fetchall()

    if len(available_seats) < booking.number_of_seats:
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="Not enough seats available")

    # Try to book in the same row first
    booked_seats = []
    for row in range(1, 13):
        row_seats = [seat for seat in available_seats if seat["seat_row"] == row]
        if len(row_seats) >= booking.number_of_seats:
            booked_seats = [seat["seat_id"] for seat in row_seats[:booking.number_of_seats]]
            cursor.executemany("UPDATE seats SET status = 'booked' WHERE seat_id = %s",
                               [(seat_id,) for seat_id in booked_seats])
            conn.commit()
            cursor.close()
            conn.close()
            return BookingResponse(booked_seats=booked_seats)

    # If not possible, book the nearest available seats
    booked_seats = [seat["seat_id"] for seat in available_seats[:booking.number_of_seats]]

    # Sort the seats by row and then by seat_id to ensure proximity
    sorted_seats = sorted(available_seats, key=lambda x: (x["seat_row"], x["seat_id"]))
    booked_seats = [seat["seat_id"] for seat in sorted_seats[:booking.number_of_seats]]

    cursor.executemany("UPDATE seats SET status = 'booked' WHERE seat_id = %s",
                       [(seat_id,) for seat_id in booked_seats])
    conn.commit()

    cursor.close()
    conn.close()
    return BookingResponse(booked_seats=booked_seats)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)
