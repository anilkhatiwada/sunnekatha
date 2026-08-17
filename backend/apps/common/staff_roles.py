"""Canonical, additive staff-role permission matrix.

Permission strings are explicit so role changes remain reviewable. The setup command
adds these permissions but deliberately leaves any separately configured permissions
untouched.
"""


def model_permissions(app_label, model_name, *actions):
    return {f"{app_label}.{action}_{model_name}" for action in actions}


VIEW_CONTENT = set().union(
    model_permissions("catalog", "literarywork", "view"),
    model_permissions("catalog", "album", "view"),
    model_permissions("catalog", "audiotrack", "view"),
    model_permissions("authors", "author", "view"),
    model_permissions("narrators", "narrator", "view"),
    model_permissions("taxonomy", "genre", "view"),
    model_permissions("taxonomy", "mood", "view"),
    model_permissions("taxonomy", "language", "view"),
    model_permissions("taxonomy", "contentcategory", "view"),
)

EDIT_CONTENT = set().union(
    VIEW_CONTENT,
    model_permissions("catalog", "literarywork", "add", "change"),
    model_permissions("catalog", "album", "add", "change"),
    model_permissions("catalog", "audiotrack", "add", "change"),
    model_permissions("authors", "author", "add", "change"),
    model_permissions("narrators", "narrator", "add", "change"),
    model_permissions("taxonomy", "genre", "add", "change"),
    model_permissions("taxonomy", "mood", "add", "change"),
    model_permissions("taxonomy", "language", "add", "change"),
    model_permissions("taxonomy", "contentcategory", "add", "change"),
)

MANAGE_PLAYLISTS = set().union(
    model_permissions("playlists", "playlist", "view", "add", "change"),
    model_permissions("playlists", "playlistitem", "view", "add", "change"),
)

MANAGE_HOMEPAGE = set().union(
    model_permissions("home", "homesection", "view", "add", "change"),
    model_permissions("home", "homesectionitem", "view", "add", "change"),
)

MANAGE_AUDIO = set().union(
    model_permissions("catalog", "audiotrack", "view", "change"),
    model_permissions("catalog", "audioprocessingjob", "view", "change"),
    model_permissions("uploads", "uploadsession", "view", "add", "change"),
    model_permissions(
        "audio_ads",
        "audioadvertisement",
        "view",
        "add",
        "change",
        "delete",
    ),
    model_permissions("audio_ads", "audioadvertisementplayback", "view"),
    {"catalog.retry_audioprocessingjob"},
)

VIEW_RIGHTS = set().union(
    model_permissions("catalog", "rightsholder", "view"),
    model_permissions("catalog", "copyrightlicense", "view"),
    model_permissions("catalog", "permissiondocument", "view"),
    model_permissions("catalog", "permissiondocumentaudit", "view"),
)

MANAGE_RIGHTS = set().union(
    VIEW_RIGHTS,
    model_permissions("catalog", "rightsholder", "add", "change"),
    model_permissions("catalog", "copyrightlicense", "add", "change"),
    model_permissions("catalog", "permissiondocument", "add", "change"),
    {"catalog.verify_permissiondocument"},
)

MANAGE_USERS = model_permissions("accounts", "user", "view", "add", "change")

MANAGE_SUBSCRIPTIONS = set().union(
    model_permissions(
        "subscriptions",
        "subscriptionplan",
        "view",
        "add",
        "change",
    ),
    model_permissions(
        "subscriptions",
        "usersubscription",
        "view",
        "change",
    ),
    model_permissions(
        "subscriptions",
        "contententitlement",
        "view",
        "add",
        "change",
    ),
    model_permissions("subscriptions", "subscriptionaudit", "view"),
)

VIEW_ANALYTICS = set().union(
    *(
        model_permissions("analytics", model, "view")
        for model in (
            "dailyplatformmetric",
            "dailytrackmetric",
            "dailyauthormetric",
            "dailynarratormetric",
            "dailyplaylistmetric",
        )
    )
)
EXPORT_ANALYTICS = {"analytics.export_analytics_dashboard"}

REVIEW_CONTENT = {
    "catalog.approve_audiotrack",
    "catalog.view_pendingreviewtrack",
    "catalog.change_pendingreviewtrack",
    "catalog.view_trackreviewevent",
}

PUBLISH_CONTENT = {
    "catalog.publish_audiotrack",
}

SYSTEM_ADMINISTRATION = set().union(
    model_permissions("auth", "group", "view", "add", "change"),
    model_permissions("auth", "permission", "view"),
    model_permissions("common", "administrativeaudit", "view"),
    {"common.import_metadata", "common.export_metadata"},
)

ROLE_PERMISSIONS = {
    "Publisher": EDIT_CONTENT
    | REVIEW_CONTENT
    | PUBLISH_CONTENT
    | MANAGE_PLAYLISTS
    | MANAGE_HOMEPAGE
    | VIEW_RIGHTS,
    "Senior Editor": EDIT_CONTENT
    | REVIEW_CONTENT
    | MANAGE_PLAYLISTS
    | MANAGE_HOMEPAGE
    | VIEW_RIGHTS,
    "Editor": EDIT_CONTENT | MANAGE_HOMEPAGE | VIEW_RIGHTS,
    "Audio Manager": VIEW_CONTENT | MANAGE_AUDIO,
    "Playlist Curator": VIEW_CONTENT | MANAGE_PLAYLISTS,
    "Copyright Manager": VIEW_CONTENT | MANAGE_RIGHTS,
    "Support Staff": MANAGE_USERS | MANAGE_SUBSCRIPTIONS,
    "Analytics Viewer": VIEW_ANALYTICS | EXPORT_ANALYTICS,
}

ROLE_PERMISSIONS["Super Administrator"] = set().union(
    *ROLE_PERMISSIONS.values(),
    SYSTEM_ADMINISTRATION,
    {"catalog.approve_own_audiotrack"},
)

ROLE_NAMES = tuple(ROLE_PERMISSIONS)
