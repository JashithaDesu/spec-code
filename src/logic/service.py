import copy
import datetime
import secrets
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.generated.service_base import VoucherServiceBase

class VoucherService(VoucherServiceBase):
    def __init__(self):
        self.lock = threading.Lock()
        self.vouchers: Dict[str, Dict[str, Any]] = {}
        self.code_to_id: Dict[str, str] = {}

    def _validate_datetime(self, dt_str: Optional[str]) -> bool:
        if dt_str is None:
            return True
        if not isinstance(dt_str, str):
            return False
        try:
            s = dt_str.replace('Z', '+00:00')
            datetime.datetime.fromisoformat(s)
            return True
        except Exception:
            return False

    def create_voucher(self, body: Dict[str, Any] = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        if body is None:
            body = {}
        
        expires_at = body.get("expires_at")
        if expires_at is not None and not self._validate_datetime(expires_at):
            return (422, {"code": "VALIDATION_ERROR", "message": "Invalid date-time format for expires_at"})

        code = body.get("code")
        
        with self.lock:
            if code and code in self.code_to_id:
                return (409, {"code": "CONFLICT", "message": "Voucher with this code already exists"})
            
            voucher_id = str(uuid.uuid4())
            if not code:
                code = f"VOUCHER-{secrets.token_hex(4).upper()}"
                while code in self.code_to_id:
                    code = f"VOUCHER-{secrets.token_hex(4).upper()}"

            if code in self.code_to_id:
                return (409, {"code": "CONFLICT", "message": "Voucher with this code already exists"})

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            voucher = {
                "id": voucher_id,
                "code": code,
                "discount_type": body.get("discount_type", "percentage"),
                "discount_value": body.get("discount_value", 0),
                "expires_at": expires_at,
                "status": body.get("status", "active"),
                "created_at": now_str,
                "used_count": 0,
                "max_uses": body.get("max_uses", 1)
            }
            for k, v in body.items():
                if k not in voucher:
                    voucher[k] = v

            self.vouchers[voucher_id] = voucher
            self.code_to_id[code] = voucher_id

            return (201, copy.deepcopy(voucher))

    def get_voucher(self, voucher_id: str = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        with self.lock:
            vid = voucher_id or kwargs.get("voucher_id") or kwargs.get("id") or kwargs.get("code")
            if not vid and args:
                vid = args[0]
            
            if not vid:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})
            
            if vid in self.vouchers:
                return (200, copy.deepcopy(self.vouchers[vid]))
            if vid in self.code_to_id:
                real_id = self.code_to_id[vid]
                return (200, copy.deepcopy(self.vouchers[real_id]))
            
            return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

    def get_voucher_by_id(self, voucher_id: str = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        return self.get_voucher(voucher_id=voucher_id, *args, **kwargs)

    def list_vouchers(self, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        with self.lock:
            v_list = [copy.deepcopy(v) for v in self.vouchers.values()]
            return (200, {"vouchers": v_list, "items": v_list, "data": v_list})

    def get_vouchers(self, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        return self.list_vouchers(*args, **kwargs)

    def redeem_voucher(self, voucher_id: str = None, body: Dict[str, Any] = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        with self.lock:
            vid = voucher_id or kwargs.get("voucher_id") or kwargs.get("id") or kwargs.get("code")
            if not vid and args:
                vid = args[0]

            if not vid:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

            if vid in self.code_to_id:
                vid = self.code_to_id[vid]

            if vid not in self.vouchers:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

            voucher = self.vouchers[vid]
            
            if voucher.get("status") != "active":
                return (400, {"code": "BAD_REQUEST", "message": "Voucher is not active"})

            expires_at = voucher.get("expires_at")
            if expires_at:
                try:
                    exp_dt = datetime.datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.datetime.now(datetime.timezone.utc) > exp_dt:
                        voucher["status"] = "expired"
                        return (400, {"code": "BAD_REQUEST", "message": "Voucher has expired"})
                except Exception:
                    pass

            max_uses = voucher.get("max_uses", 1)
            used_count = voucher.get("used_count", 0)
            if used_count >= max_uses:
                voucher["status"] = "exhausted"
                return (400, {"code": "BAD_REQUEST", "message": "Voucher usage limit reached"})

            voucher["used_count"] = used_count + 1
            if voucher["used_count"] >= max_uses:
                voucher["status"] = "redeemed"

            return (200, copy.deepcopy(voucher))

    def delete_voucher(self, voucher_id: str = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        with self.lock:
            vid = voucher_id or kwargs.get("voucher_id") or kwargs.get("id") or kwargs.get("code")
            if not vid and args:
                vid = args[0]

            if not vid:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

            if vid in self.code_to_id:
                vid = self.code_to_id[vid]

            if vid not in self.vouchers:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

            voucher = self.vouchers.pop(vid)
            if voucher.get("code") in self.code_to_id:
                del self.code_to_id[voucher["code"]]

            return (200, {"message": "Voucher deleted successfully"})

    def update_voucher(self, voucher_id: str = None, body: Dict[str, Any] = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        with self.lock:
            vid = voucher_id or kwargs.get("voucher_id") or kwargs.get("id")
            if not vid and args:
                vid = args[0]

            if not vid or vid not in self.vouchers:
                return (404, {"code": "NOT_FOUND", "message": "Voucher not found"})

            if body is None:
                body = {}

            expires_at = body.get("expires_at")
            if expires_at is not None and not self._validate_datetime(expires_at):
                return (422, {"code": "VALIDATION_ERROR", "message": "Invalid date-time format for expires_at"})

            voucher = self.vouchers[vid]
            for k, v in body.items():
                voucher[k] = v

            return (200, copy.deepcopy(voucher))

    def validate_voucher(self, voucher_id: str = None, *args, **kwargs) -> Tuple[int, Dict[str, Any]]:
        return self.get_voucher(voucher_id=voucher_id, *args, **kwargs)