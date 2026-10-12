import json
from typing import Any, Dict, List, Optional

from ai.repository_utils import (
    decode_row,
    fetch_active_provider,
    fetch_all_provider_profiles,
    fetch_provider_by_profile_key,
    maybe_preserve,
    provider_label_for,
)
from database.models import get_db


class ProviderRepositoryMixin:
    @staticmethod
    def build_profile_key(provider: str, model: str, profile_key: Optional[str] = None) -> str:
        explicit = str(profile_key or '').strip().lower()
        if explicit:
            return explicit
        normalized_provider = str(provider or 'provider').strip().lower().replace(' ', '-')
        normalized_model = str(model or 'default').strip().lower().replace(' ', '-') or 'default'
        return f"{normalized_provider}-{normalized_model}"

    @staticmethod
    def build_display_name(provider: str, model: str, display_name: Optional[str] = None) -> str:
        explicit = str(display_name or '').strip()
        if explicit:
            return explicit
        return f"{provider_label_for(provider)} / {str(model or 'default').strip() or 'default'}"

    def upsert_provider_settings(
        self,
        provider: str,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        models: Optional[List[str]] = None,
        base_url: Optional[str] = None,
        is_active: bool = False,
        profile_key: Optional[str] = None,
        display_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        resolved_model_input = str(model or '').strip()
        normalized_models = [str(item).strip() for item in (models or []) if str(item).strip()]
        if resolved_model_input and resolved_model_input not in normalized_models:
            normalized_models.insert(0, resolved_model_input)
        resolved_profile_key = self.build_profile_key(provider, resolved_model_input or 'default', profile_key)
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            existing_row = fetch_provider_by_profile_key(cursor, resolved_profile_key)
            existing = decode_row(existing_row)

            existing_models = []
            if existing and existing.get("models_json"):
                try:
                    existing_models = [str(item).strip() for item in json.loads(existing.get("models_json") or "[]") if str(item).strip()]
                except Exception:
                    existing_models = []
            resolved_models = normalized_models or existing_models or ([resolved_model_input] if resolved_model_input else [])
            resolved_api_key = maybe_preserve(existing, api_key, "api_key") if existing else api_key
            resolved_model = (resolved_models[0] if resolved_models else None) or (maybe_preserve(existing, resolved_model_input or None, "model") if existing else resolved_model_input)
            resolved_base_url = maybe_preserve(existing, base_url, "base_url") if existing else base_url
            resolved_display_name = self.build_display_name(provider, resolved_model or 'default', display_name)

            if is_active:
                cursor.execute("UPDATE ai_provider_settings SET is_active = 0, updated_at = CURRENT_TIMESTAMP")

            cursor.execute(
                """
                INSERT INTO ai_provider_settings (
                    profile_key, display_name, provider, provider_label, api_key, model, models_json, base_url, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(profile_key) DO UPDATE SET
                    display_name = excluded.display_name,
                    provider = excluded.provider,
                    provider_label = excluded.provider_label,
                    api_key = excluded.api_key,
                    model = excluded.model,
                    models_json = excluded.models_json,
                    base_url = excluded.base_url,
                    is_active = excluded.is_active,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    resolved_profile_key,
                    resolved_display_name,
                    provider,
                    provider_label_for(provider),
                    resolved_api_key,
                    resolved_model,
                    json.dumps(resolved_models),
                    resolved_base_url,
                    int(is_active),
                ),
            )
            conn.commit()
            return decode_row(fetch_provider_by_profile_key(cursor, resolved_profile_key))

    def get_active_provider(self) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_active_provider(cursor)
            return decode_row(row) or None

    @staticmethod
    def mask_api_key(api_key: Optional[str]) -> Optional[str]:
        if not api_key:
            return None
        suffix = api_key[-4:] if len(api_key) >= 4 else api_key
        return f"••••{suffix}"

    def sanitize_provider_settings(self, settings: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if settings is None:
            return None
        payload = dict(settings)
        payload["provider_label"] = payload.get("provider_label") or provider_label_for(str(payload.get("provider") or ""))
        payload["display_name"] = payload.get("display_name") or self.build_display_name(
            str(payload.get("provider") or ''),
            str(payload.get("model") or 'default'),
            payload.get("display_name"),
        )
        payload["profile_key"] = payload.get("profile_key") or self.build_profile_key(
            str(payload.get("provider") or ''),
            str(payload.get("model") or 'default'),
            payload.get("profile_key"),
        )
        raw_models = payload.get("models_json")
        try:
            models = [str(item).strip() for item in json.loads(raw_models or "[]") if str(item).strip()]
        except Exception:
            models = []
        if payload.get("model") and payload.get("model") not in models:
            models.insert(0, str(payload.get("model")))
        payload["models"] = models
        raw_api_key = str(payload.get("api_key") or "") or None
        payload["api_key_masked"] = self.mask_api_key(raw_api_key)
        payload["has_api_key"] = bool(raw_api_key)
        payload["api_key"] = None
        payload["is_active"] = bool(payload.get("is_active"))
        return payload

    def get_provider_by_profile_key(self, profile_key: str) -> Optional[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            row = fetch_provider_by_profile_key(cursor, profile_key)
            return decode_row(row) or None

    def list_providers(self) -> List[Dict[str, Any]]:
        with get_db(self.db_path) as conn:
            cursor = conn.cursor()
            return [decode_row(row) for row in fetch_all_provider_profiles(cursor)]
