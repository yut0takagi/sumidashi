from decimal import Decimal

import boto3
from fastapi import HTTPException


class Invoice:
    def __init__(self, invoice_id: str, amount: Decimal) -> None:
        if amount <= 0:
            raise HTTPException(status_code=400, detail="amount must be positive")
        self._id = invoice_id
        self._amount = amount

    def archive(self, bucket: str) -> None:
        s3 = boto3.client("s3")
        s3.put_object(
            Bucket=bucket,
            Key=f"invoices/{self._id}.txt",
            Body=str(self._amount).encode(),
        )
