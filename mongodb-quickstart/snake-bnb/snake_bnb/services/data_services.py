from datetime import datetime, timedelta
from typing import List

import bson

from data.bookings import Booking
from data.cages import Cage
from data.owners import Owner
from data.snakes import Snake


def create_account(name: str, email: str) -> Owner:
    owner = Owner()
    owner.name = name
    owner.email = email

    owner.save()

    return owner


def find_account_by_email(email: str) -> Owner:
    owner = Owner.objects(email=email).first()  # pylint: disable=no-member
    return owner


def register_cage(
    active_account: Owner, name, allow_dangerous, has_toys, carpeted, meters, price
) -> Cage:
    cage = Cage()
    cage.name = name
    cage.square_meters = meters
    cage.is_carpeted = carpeted
    cage.has_toys = has_toys
    cage.allow_dangerous_snakes = allow_dangerous
    cage.price = price

    cage.save()

    account = find_account_by_email(active_account.email)
    account.cage_ids.append(cage.id)  # pylint: disable=no-member
    account.save()

    return cage


def find_cages_for_user(account: Owner) -> List[Cage]:
    query = Cage.objects(id__in=account.cage_ids)  # pylint: disable=no-member
    return list(query)


def add_available_date(selected_cage: Cage, start_date: datetime, days: int) -> Cage:
    booking = Booking()
    booking.check_in_date = start_date
    booking.check_out_date = start_date + timedelta(days=days)

    cage = Cage.objects(id=selected_cage.id).first()  # pylint: disable=no-member
    cage.bookings.append(booking)
    cage.save()

    return cage


def add_snake(account: Owner, name, length, species, is_venomous) -> Snake:
    snake = Snake()
    snake.name = name
    snake.length = length
    snake.species = species
    snake.is_venomous = is_venomous
    snake.save()

    owner = find_account_by_email(account.email)
    owner.snake_ids.append(snake.id)  # pylint: disable=no-member
    owner.save()

    return snake


def get_snakes_for_user(user_id: bson.ObjectId) -> List[Snake]:
    owner = Owner.objects(id=user_id).first()  # pylint: disable=no-member
    snakes = Snake.objects(id__in=owner.snake_ids).all()  # pylint: disable=no-member
    return list(snakes)


def get_available_cages(
    checkin: datetime, checkout: datetime, snake: Snake
) -> List[Cage]:
    min_size = snake.length / 4
    query = (
        Cage.objects()  # pylint: disable=no-member
        .filter(square_meters__gte=min_size)
        .filter(bookings__check_in_date__lte=checkin)
        .filter(bookings__check_out_date__gte=checkin)
    )

    if snake.is_venomous:
        query = query.filter(allow_dangerous_snakes=True)

    cages = query.order_by("price", "-square_meters")

    final_cages = []
    for c in cages:
        for b in c.bookings:
            if (
                b.check_in_date <= checkin
                and b.check_out_date >= checkout
                and b.guest_snake_id is None
            ):
                final_cages.append(c)

    return final_cages


def book_cage(account, snake, cage, checkin, checkout):
    booking: Booking = None

    for b in cage.bookings:
        if (
            b.check_in_date <= checkin
            and b.check_out_date >= checkout
            and b.guest_snake_id is None
        ):
            booking = b
            break

    booking.guest_owner_id = account.id
    booking.guest_snake_id = snake.id
    booking.booked_date = datetime.now()

    cage.save()


def get_bookings_for_user(email: str) -> List[Booking]:
    account = find_account_by_email(email)

    booked_cages = (
        Cage.objects()  # pylint: disable=no-member
        .filter(bookings__guest_owner_id=account.id)
        .only("bookings", "name")
    )

    def map_cage_to_booking(cage, booking):
        booking.cage = cage
        return booking

    bookings = [
        map_cage_to_booking(cage, booking)
        for cage in booked_cages
        for booking in cage.bookings
        if booking.guest_owner_id == account.id
    ]

    return bookings
