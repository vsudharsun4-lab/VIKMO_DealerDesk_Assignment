"""seed_data management command.

Loads catalogue.csv (Products + stock) and dealers.csv into the database.
Running it multiple times must not create duplicates (idempotent via update_or_create).
"""
import csv
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.management.base import BaseCommand

from products.models import Product, Dealer


class Command(BaseCommand):
    help = "Load the files in data/ into the database. Safe to run more than once."

    def handle(self, *args, **options):
        data_dir = settings.DATA_DIR

        # ── Products ──────────────────────────────────────────────────────────
        catalogue_path = data_dir / "catalogue.csv"
        products_created = products_updated = 0
        with open(catalogue_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                sku = row["sku"].strip()
                try:
                    price = Decimal(row["price"].strip())
                except InvalidOperation:
                    self.stderr.write(f"Skipping product {sku}: invalid price {row['price']!r}")
                    continue
                try:
                    stock = int(row["stock"].strip())
                except ValueError:
                    stock = 0

                obj, created = Product.objects.update_or_create(
                    sku=sku,
                    defaults=dict(
                        name=row["name"].strip(),
                        category=row["category"].strip(),
                        brand=row["brand"].strip(),
                        vehicle_fitment=row["vehicle_fitment"].strip(),
                        price=price,
                        stock=stock,
                        description=row.get("description", "").strip(),
                    ),
                )
                if created:
                    products_created += 1
                else:
                    products_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Products: {products_created} created, {products_updated} updated"
            )
        )

        # ── Dealers ───────────────────────────────────────────────────────────
        dealers_path = data_dir / "dealers.csv"
        dealers_created = dealers_updated = 0
        with open(dealers_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                dealer_code = row["dealer_code"].strip()
                try:
                    credit_limit = Decimal(row.get("credit_limit", "0").strip() or "0")
                except InvalidOperation:
                    credit_limit = Decimal("0")

                obj, created = Dealer.objects.update_or_create(
                    dealer_code=dealer_code,
                    defaults=dict(
                        name=row["name"].strip(),
                        city=row.get("city", "").strip(),
                        phone=row.get("phone", "").strip(),
                        email=row.get("email", "").strip(),
                        gstin=row.get("gstin", "").strip(),
                        credit_limit=credit_limit,
                    ),
                )
                if created:
                    dealers_created += 1
                else:
                    dealers_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Dealers: {dealers_created} created, {dealers_updated} updated"
            )
        )

        self.stdout.write(self.style.SUCCESS("seed_data complete."))
