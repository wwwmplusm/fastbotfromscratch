from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    entries: Mapped[list["FoodEntryORM"]] = relationship(back_populates="user")


class FoodEntryORM(Base):
    __tablename__ = "food_entries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'cancelled', 'expired')",
            name="ck_food_entries_status",
        ),
        Index("ix_food_entries_user_status_eaten", "user_id", "status", "eaten_at"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    photo_file_id: Mapped[str | None] = mapped_column(Text)
    eaten_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calories: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbohydrates: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    recognition_error: Mapped[str | None] = mapped_column(String(40))

    user: Mapped[UserORM] = relationship(back_populates="entries")
    items: Mapped[list["FoodEntryItemORM"]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="FoodEntryItemORM.position",
    )


class FoodEntryItemORM(Base):
    __tablename__ = "food_entry_items"
    __table_args__ = (CheckConstraint("weight_g > 0", name="ck_food_entry_items_weight"),)

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True)
    entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("food_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    weight_g: Mapped[Decimal] = mapped_column(Numeric(7, 1), nullable=False)
    calories: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbohydrates: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    calories_per_100g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    protein_per_100g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    fat_per_100g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    carbohydrates_per_100g: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    nutrition_source: Mapped[str] = mapped_column(String(20), nullable=False)
    recognition_note: Mapped[str | None] = mapped_column(Text)

    entry: Mapped[FoodEntryORM] = relationship(back_populates="items")
