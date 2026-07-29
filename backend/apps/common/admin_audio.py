"""Reusable, lazy, permission-checked audio previews for Django Admin."""

from __future__ import annotations

import json
from typing import TypedDict

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.safestring import mark_safe
from rest_framework.exceptions import APIException


class AdminAudioSource(TypedDict):
    quality: str
    label: str
    available: bool


class SecureAudioPreviewAdminMixin:
    """Render a player that requests media URLs only after explicit playback."""

    class Media:
        css = {"all": ("admin/css/secure-audio-preview.css",)}
        js = ("admin/js/secure-audio-preview.js",)

    def get_urls(self):
        route_name = f"{self.opts.app_label}_{self.opts.model_name}_audio_delivery"
        custom_urls = [
            path(
                "<path:object_id>/audio-delivery/<str:quality>/",
                self.admin_site.admin_view(self.audio_delivery_view),
                name=route_name,
            )
        ]
        return custom_urls + super().get_urls()

    def get_audio_preview_sources(self, obj) -> list[AdminAudioSource]:
        raise NotImplementedError

    def get_audio_preview_title(self, obj) -> str:
        return str(obj)

    def get_audio_preview_duration(self, obj) -> int | None:
        return None

    @staticmethod
    def format_audio_duration(seconds: int | None) -> str:
        if seconds is None:
            return "--:--"
        whole = max(0, int(seconds))
        hours, remainder = divmod(whole, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    def resolve_audio_delivery(self, obj, *, quality, request):
        raise NotImplementedError

    def render_audio_preview(self, obj):
        if obj is None or obj.pk is None:
            return "Audio preview is available after saving."
        sources = self.get_audio_preview_sources(obj)
        available = any(source["available"] for source in sources)
        duration = self.get_audio_preview_duration(obj)
        route_name = (
            f"admin:{self.opts.app_label}_{self.opts.model_name}_audio_delivery"
        )
        payload = [
            {
                **source,
                "url": (
                    reverse(
                        route_name,
                        kwargs={"object_id": obj.pk, "quality": source["quality"]},
                    )
                    if source["available"]
                    else None
                ),
            }
            for source in sources
        ]
        html = render_to_string(
            "admin/widgets/secure_audio_preview.html",
            {
                "widget_id": f"secure-audio-{self.opts.app_label}-{obj.pk}",
                "title": self.get_audio_preview_title(obj),
                "duration": duration,
                "duration_display": self.format_audio_duration(duration),
                "sources_json": json.dumps(payload),
                "has_available_audio": available,
                "sources": sources,
            },
        )
        return mark_safe(html)

    def audio_delivery_view(self, request, object_id, quality):
        obj = self.get_object(request, object_id)
        if obj is None:
            raise Http404
        if not self.has_view_or_change_permission(request, obj):
            raise PermissionDenied
        sources = {
            source["quality"]: source for source in self.get_audio_preview_sources(obj)
        }
        source = sources.get(quality)
        if source is None or not source["available"]:
            return JsonResponse(
                {
                    "detail": "This audio quality is unavailable.",
                    "code": "audio_unavailable",
                },
                status=404,
            )
        try:
            delivery = self.resolve_audio_delivery(
                obj,
                quality=quality,
                request=request,
            )
        except APIException as exc:
            response = JsonResponse(
                {
                    "detail": str(exc.detail),
                    "code": getattr(exc, "default_code", "media_delivery_error"),
                },
                status=exc.status_code,
            )
        else:
            expires_at = delivery.get("expiresAt")
            response = JsonResponse(
                {
                    "quality": delivery["quality"],
                    "url": delivery["url"],
                    "expiresAt": expires_at.isoformat() if expires_at else None,
                }
            )
        response["Cache-Control"] = "private, no-store"
        response["Pragma"] = "no-cache"
        return response
