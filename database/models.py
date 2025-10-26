from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Integer, Float, Date, ForeignKey, Index, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database.base import Base


class Article(Base):
    __tablename__ = "articles"

    article_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    product_code: Mapped[int] = mapped_column(Integer, nullable=False)
    prod_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_type_no: Mapped[int] = mapped_column(Integer, nullable=False)
    product_type_name: Mapped[str] = mapped_column(String(100), nullable=False)
    product_group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    graphical_appearance_no: Mapped[int] = mapped_column(Integer, nullable=False)
    graphical_appearance_name: Mapped[str] = mapped_column(String(100), nullable=False)
    colour_group_code: Mapped[int] = mapped_column(Integer, nullable=False)
    colour_group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    perceived_colour_value_id: Mapped[int] = mapped_column(Integer, nullable=False)
    perceived_colour_value_name: Mapped[str] = mapped_column(String(100), nullable=False)
    perceived_colour_master_id: Mapped[int] = mapped_column(Integer, nullable=False)
    perceived_colour_master_name: Mapped[str] = mapped_column(String(100), nullable=False)
    department_no: Mapped[int] = mapped_column(Integer, nullable=False)
    department_name: Mapped[str] = mapped_column(String(100), nullable=False)
    index_code: Mapped[str] = mapped_column(String(10), nullable=False)
    index_name: Mapped[str] = mapped_column(String(100), nullable=False)
    index_group_no: Mapped[int] = mapped_column(Integer, nullable=False)
    index_group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    section_no: Mapped[int] = mapped_column(Integer, nullable=False)
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)
    garment_group_no: Mapped[int] = mapped_column(Integer, nullable=False)
    garment_group_name: Mapped[str] = mapped_column(String(100), nullable=False)
    detail_desc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="article"
    )

    __table_args__ = (
        Index('idx_product_code', 'product_code'),
        Index('idx_product_type_no', 'product_type_no'),
        Index('idx_department_no', 'department_no'),
    )

    def __repr__(self) -> str:
        return f"<Article(article_id={self.article_id}, prod_name='{self.prod_name}')>"


class Customer(Base):
    __tablename__ = "customers"

    customer_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    fn: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    active: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    club_member_status: Mapped[str] = mapped_column(String(50), nullable=False)
    fashion_news_frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    postal_code: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Campos de autenticación (nuevos)
    name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_authenticated: Mapped[bool] = mapped_column(default=False)  # True si tiene credenciales
    created_at: Mapped[Optional[datetime]] = mapped_column(nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="customer"
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="customer", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index('idx_club_member_status', 'club_member_status'),
        Index('idx_age', 'age'),
        Index('idx_email', 'email'),
        Index('idx_is_authenticated', 'is_authenticated'),
    )

    def __repr__(self) -> str:
        return f"<Customer(customer_id='{self.customer_id[:10]}...', age={self.age})>"


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    t_dat: Mapped[datetime] = mapped_column(Date, nullable=False)
    customer_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("customers.customer_id"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.article_id"), nullable=False
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    sales_channel_id: Mapped[int] = mapped_column(Integer, nullable=False)

    customer: Mapped["Customer"] = relationship("Customer", back_populates="transactions")
    article: Mapped["Article"] = relationship("Article", back_populates="transactions")

    __table_args__ = (
        Index('idx_t_dat', 't_dat'),
        Index('idx_customer_id', 'customer_id'),
        Index('idx_article_id', 'article_id'),
        Index('idx_sales_channel_id', 'sales_channel_id'),
    )

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, t_dat='{self.t_dat}', price={self.price})>"


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("customers.customer_id"), nullable=False
    )
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.article_id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    added_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relaciones
    customer: Mapped["Customer"] = relationship("Customer", back_populates="cart_items")
    article: Mapped["Article"] = relationship("Article")

    __table_args__ = (
        Index('idx_cart_customer_id', 'customer_id'),
        Index('idx_cart_article_id', 'article_id'),
        Index('idx_cart_is_active', 'is_active'),
        Index('idx_cart_customer_article', 'customer_id', 'article_id'),  # Para consultas rápidas
    )

    def __repr__(self) -> str:
        return f"<CartItem(id={self.id}, customer_id='{self.customer_id[:10]}...', article_id={self.article_id}, quantity={self.quantity})>"
