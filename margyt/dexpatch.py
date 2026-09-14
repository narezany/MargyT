"""Rewriting the calls that ask the phone where it is.

Without root there is no Xposed, and without Xposed there is nothing to hook at
runtime -- so the calls are redirected in the bytecode instead. Each one becomes
a static call into the mod:

    invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getSimCountryIso()Ljava/lang/String;
    invoke-static  {v0}, Lcat/narezany/margyt/Region;->getSimCountryIso(Landroid/telephony/TelephonyManager;)Ljava/lang/String;

The instruction format (35c), the register count and the return type all match,
so nothing around the call has to be renumbered: the receiver just becomes the
first argument.

Targets are found by signature, never by offset or by file name, so a new
TikTok release does not move them. Of the apk's fifty-two dex files, the four
or five that mention telephony at all are the only ones taken apart; the rest
are copied across untouched, which is the difference between a build that takes
minutes and one that takes hours.
"""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from typing import Dict, List, Optional, Tuple

TELEPHONY = "Landroid/telephony/TelephonyManager;"
REGION = "Lcat/narezany/margyt/Region;"
ACCENT = "Lcat/narezany/margyt/Accent;"
DOWNLOAD = "Lcat/narezany/margyt/Download;"
FEED = "Lcat/narezany/margyt/Feed;"

# TikTok's own models. Every name here is a real one, read out of the apk's
# method and field tables rather than guessed, and each is answered by a static
# of ours with the receiver moved into the first argument -- the same 35c
# instruction, the same register count, the same return type.
VIDEO = "Lcom/ss/android/ugc/aweme/feed/model/Video;"
ACL = "Lcom/ss/android/ugc/aweme/feed/model/ACLCommonShare;"
AWEME = "Lcom/ss/android/ugc/aweme/feed/model/Aweme;"
USER = "Lcom/ss/android/ugc/aweme/profile/model/User;"
VIDEO_CONTROL = "Lcom/ss/android/ugc/aweme/feed/model/VideoControl;"
FEED_ITEM_LIST = "Lcom/ss/android/ugc/aweme/feed/model/FeedItemList;"
PHOTO_IMAGE = "Lcom/ss/android/ugc/aweme/feed/model/PhotoModeImageUrlModel;"
ACCOUNT_SERVICE = "Lcom/ss/android/ugc/aweme/IAccountUserService;"
ACCOUNT = "Lcat/narezany/margyt/Account;"
COMMENTS = "Lcat/narezany/margyt/Comments;"
COMMENT_FILTER = "Lcat/narezany/margyt/CommentFilter;"
COMMENT_IMAGE = "Lcom/ss/android/ugc/aweme/comment/model/CommentImageStruct;"
COMMENT = "Lcom/ss/android/ugc/aweme/comment/model/Comment;"
COMMENT_STICKER = "Lcom/ss/android/ugc/aweme/comment/model/CommentStickerStruct;"
WATERMARK = "Lcat/narezany/margyt/Watermark;"
FLAGS = "Lcat/narezany/margyt/Flags;"
SOUND = "Lcat/narezany/margyt/Sound;"
BADGE = "Lcat/narezany/margyt/Badge;"
AVATARS = "Lcat/narezany/margyt/Avatars;"
STICKERS = "Lcat/narezany/margyt/Stickers;"
STREAKS = "Lcat/narezany/margyt/Streaks;"
STREAK_DATA = "Lcom/ss/android/ugc/aweme/im/streak/api/StreakData;"
STREAK_SERVICE = "Lcom/ss/android/ugc/aweme/im/streak/api/IStreakService;"
STICKER_ITEM = "Lcom/ss/android/ugc/aweme/im/common/model/StickerItem;"
STICKER_IMAGE = "Lcom/ss/android/ugc/aweme/im/common/model/StickerImage;"
STICKER_BASE = "Lcom/ss/android/ugc/aweme/im/common/model/StickerBase;"
STICKER_CLICK = "Lcom/ss/android/ugc/aweme/im/messagelist/api/ability/MessageListStickerClickAbility;"
STICKER_TEMPLATE = "Lcom/ss/android/ugc/aweme/im/message/template/card/StickerTemplate;"
TEXT_VIEW = "Landroid/widget/TextView;"
CHAR_SEQUENCE = "Ljava/lang/CharSequence;"
SEEKBAR = "Lcat/narezany/margyt/Seekbar;"
MUSIC = "Lcom/ss/android/ugc/aweme/music/model/Music;"

# A method whose name is real on a class whose name is not. Matching the owner
# would mean writing down an obfuscated name that changes every release, so the
# owner is left open and the receiver arrives as a plain Object -- which is why
# the mod calls the original back by reflection rather than directly.
WILD_SOURCES: List[Tuple[str, str, str, str]] = [
    ("setSeekBarShowType", "(I)V", "(Ljava/lang/Object;I)V", SEEKBAR),
]

# A sticker touched in a conversation.
#
# The interface is MessageListStickerClickAbility and the type it is handed is
# StickerTemplate, both real names -- but a call site names whatever static
# type it is holding, which is the class implementing the interface, so the
# owner is left open. What is written down instead is each method's exact
# shape, obfuscated parameter types and all: those move between releases, and a
# release that moves them leaves the rules matching nothing, which is a feature
# that does not appear rather than an app that breaks.
#
# Everything but the sticker itself arrives as Object -- a reference is a
# reference as far as the verifier is concerned -- which is what keeps a fifth
# obfuscated name out of the mod's own source.
_TAP = "Landroid/view/View;LX/1CpA;LX/13Vd;" + STICKER_TEMPLATE
_SHEET = ("Landroid/view/View;Landroidx/fragment/app/FragmentManager;LX/13Vd;"
          + STICKER_TEMPLATE)
_INNER = "LX/1CpA;LX/13Vd;" + STICKER_TEMPLATE
_CORNER = "Lcom/ss/android/ugc/aweme/views/RoundingCornerLayout;" + STICKER_TEMPLATE
_ANY = "Ljava/lang/Object;"

WILD_SOURCES += [
    ("UP", "(%s)V" % _TAP, "(%s%s)V" % (_ANY * 4, STICKER_TEMPLATE), STICKERS),
    ("tR1", "(%s)V" % _TAP, "(%s%s)V" % (_ANY * 4, STICKER_TEMPLATE), STICKERS),
    ("dy1", "(%s)V" % _SHEET, "(%s%s)V" % (_ANY * 4, STICKER_TEMPLATE), STICKERS),
    ("Yt1", "(%s)V" % _INNER, "(%s%s)V" % (_ANY * 3, STICKER_TEMPLATE), STICKERS),
    ("XQ1", "(%s)V" % _CORNER, "(%s%s)V" % (_ANY * 2, STICKER_TEMPLATE), STICKERS),
]

# TikTok's A/B facade. The class name is real; the method names are what the
# obfuscator made of them in 46.9.42, one per type, each taking the flag's name
# and what to answer when the server said nothing. A release that renames them
# leaves the rules matching nothing, which turns the overrides off and breaks
# no part of the app.
SETTINGS_MANAGER = "Lcom/bytedance/ies/abmock/SettingsManager;"
AB_READERS: List[Tuple[str, str, str]] = [
    ("LIZ", "Ljava/lang/String;Z", "Z"),
    ("LJ", "Ljava/lang/String;I", "I"),
    ("LJFF", "Ljava/lang/String;J", "J"),
    ("LJI", "Ljava/lang/String;Ljava/lang/String;", "Ljava/lang/String;"),
    ("LIZJ", "Ljava/lang/String;F", "F"),
    ("LIZIZ", "Ljava/lang/String;D", "D"),
]
CANVAS = "Landroid/graphics/Canvas;"

# Rules that apply inside one class and nowhere else, found by a string the
# class carries rather than by its name.
#
# The stamp on a saved picture is assembled on the phone -- text and a logo
# drawn into a bitmap of their own -- and then put on the picture with a single
# Canvas.drawBitmap. Redirecting every drawBitmap in the apk would be absurd;
# redirecting the one in the class that builds the label is a rewrite of a
# single instruction. The class is X.0Hnc in 46.9.42 and will be something else
# in 46.10, but the marker in its template stays.
#
# anchor, owner, method, its descriptor, ours, the class ours lives in
# A static TikTok's obfuscation renamed but could not disguise: what it takes
# is the framework's own types and the app's own models, and no other method in
# the apk takes that. The build finds the one class that declares it, writes
# the name down for the mod to hand the call back through, and rewrites every
# call to it. Nothing obfuscated is written here, and a release that shuffles
# the names is simply found again on the next build.
#
# label, the descriptor to look for, what the mod calls it, where that lives
COMMENT_TAP = ("(Landroid/view/View;%s ZLjava/lang/String;Ljava/util/Map;"
               "Ljava/lang/String;)V" % COMMENT_STICKER).replace("; Z", ";Z")

DISCOVERED_STATICS: List[Tuple[str, str, str, str]] = [
    # a sticker in a comment, tapped. In a conversation the tap goes through an
    # interface the mod can name; here it goes to a static on a class with no
    # name worth writing down -- but it takes the view that was touched and the
    # sticker that was in it, and nothing else in the apk takes that pair.
    ("comment sticker tapped", COMMENT_TAP, "stickerTapped", COMMENTS),
]

# filled in by the build: label -> (owner, the name it carries this release)
FOUND: Dict[str, Tuple[str, str]] = {}


VIEW = "Landroid/view/View;"
LONG_CLICK = "Landroid/view/View$OnLongClickListener;"

ANCHORED_SOURCES: List[Tuple[str, str, str, str, str, str]] = [
    # A sticker in a comment already answers a long press -- TikTok sets its
    # own listener on it. So the mod does not add a gesture, it wraps the one
    # that is there: the press still does what it did, and the offer to save
    # appears beside it.
    #
    # The class is anchored by a line TikTok logs while binding a sticker,
    # which no other class in the apk carries. Anchoring matters here more than
    # anywhere: `setOnLongClickListener` is the framework's, and rewriting
    # every call to it would mean wrapping several thousand unrelated views.
    ("bindSticker: ", VIEW, "setOnLongClickListener",
     "(%s)V" % LONG_CLICK, "(%s%s)V" % (VIEW, LONG_CLICK), COMMENTS),
    ("[tiktok_logo]", CANVAS, "drawBitmap",
     "(Landroid/graphics/Bitmap;FFLandroid/graphics/Paint;)V",
     "(%sLandroid/graphics/Bitmap;FFLandroid/graphics/Paint;)V" % CANVAS, WATERMARK),
]
STRING = "Ljava/lang/String;"
URL_MODEL = "Lcom/ss/android/ugc/aweme/base/model/UrlModel;"
BOXED_BOOLEAN = "Ljava/lang/Boolean;"
LIST = "Ljava/util/List;"

# owner, method, its descriptor, ours, the class ours lives in
MODEL_SOURCES: List[Tuple[str, str, str, str, str]] = [
    # the save button's address: stamped, and the clean one beside it
    (VIDEO, "getDownloadAddr", "()%s" % URL_MODEL, "(%s)%s" % (VIDEO, URL_MODEL), DOWNLOAD),
    # what the post says may be done with it, which TikTok reads before it
    # offers a download at all
    (ACL, "getCode", "()I", "(%s)I" % ACL, DOWNLOAD),
    (ACL, "getShowType", "()I", "(%s)I" % ACL, DOWNLOAD),
    (ACL, "getTranscode", "()I", "(%s)I" % ACL, DOWNLOAD),
    # the ban on saving, on the post and on the account that made it
    (AWEME, "isPreventDownload", "()Z", "(%s)Z" % AWEME, DOWNLOAD),
    (USER, "isPreventDownload", "()Z", "(%s)Z" % USER, DOWNLOAD),
    # the page of the feed, before anything has looked at it
    (FEED_ITEM_LIST, "getItems", "()%s" % LIST, "(%s)%s" % (FEED_ITEM_LIST, LIST), FEED),
    # who is signed in. The mod does not ask -- there is no unobfuscated way to
    # reach the service -- so it listens instead: the app asks often enough,
    # and the answer goes past on its way back.
    (ACCOUNT_SERVICE, "getCurUserId", "()%s" % STRING,
     "(%s)%s" % (ACCOUNT_SERVICE, STRING), ACCOUNT),
    (ACCOUNT_SERVICE, "getCurSecUserId", "()%s" % STRING,
     "(%s)%s" % (ACCOUNT_SERVICE, STRING), ACCOUNT),
    # which sticker a comment is carrying, read as the comment is bound: the
    # view gets its long press wrapped a moment later, and this is what says
    # what that view is showing
    # Returning null for a verified author selected by the narrow local rule makes
    # TikTok skip that comment while all other comment model calls remain intact.
    (COMMENT, "getUser", "()%s" % USER,
     "(%s)%s" % (COMMENT, USER), COMMENT_FILTER),
    (COMMENT, "getStickerStruct", "()%s" % COMMENT_STICKER,
     "(Ljava/lang/Object;)%s" % COMMENT_STICKER, COMMENTS),
    (COMMENT_IMAGE, "getCropUrl", "()%s" % URL_MODEL,
     "(%s)%s" % (COMMENT_IMAGE, URL_MODEL), COMMENTS),
    (COMMENT_IMAGE, "getOriginUrl", "()%s" % URL_MODEL,
     "(%s)%s" % (COMMENT_IMAGE, URL_MODEL), COMMENTS),
    # a name, and every place that writes one. The mark rides out on the name
    # and becomes a picture on the way into the view that shows it
    (USER, "getNickname", "()Ljava/lang/String;",
     "(%s)Ljava/lang/String;" % USER, BADGE),

    # the avatar, at the sizes the app actually asks for: the mod does not need
    # to know whose profile is open, only which picture was last wanted
    (USER, "getAvatarLarger", "()%s" % URL_MODEL, "(%s)%s" % (USER, URL_MODEL), AVATARS),
    (USER, "getAvatar300", "()%s" % URL_MODEL, "(%s)%s" % (USER, URL_MODEL), AVATARS),
    (USER, "getAvatarMedium", "()%s" % URL_MODEL, "(%s)%s" % (USER, URL_MODEL), AVATARS),
    (TEXT_VIEW, "setText", "(%s)V" % CHAR_SEQUENCE,
     "(%s%s)V" % (TEXT_VIEW, CHAR_SEQUENCE), BADGE),
    (TEXT_VIEW, "setText", "(%sLandroid/widget/TextView$BufferType;)V" % CHAR_SEQUENCE,
     "(%s%sLandroid/widget/TextView$BufferType;)V" % (TEXT_VIEW, CHAR_SEQUENCE), BADGE),


    # Which conversations have a streak going. `StreakData` holds the answer
    # and every one of its fields is named plainly, but nothing in the app ever
    # reads those fields, so there is nothing to listen to there. What the app
    # does do, constantly, is ask its own streak service about a conversation --
    # and `IStreakService` is a real name with real signatures. So the mod
    # listens to the questions instead of the answers: every conversation the
    # app asks about is one the mod can then ask about itself.
    #
    # The three method names are this release's, not the app's forever. They
    # are the one version-shaped thing in the streak feature, they live here
    # rather than in the Java, and the build counts what each of them matched.
    (STREAK_SERVICE, ("J", "streakOf"), "(%sZ)%s" % (STRING, STREAK_DATA),
     "(%s%sZ)%s" % (STREAK_SERVICE, STRING, STREAK_DATA), STREAKS),
    (STREAK_SERVICE, ("a0", "hasStreak"), "(%s)Z" % STRING,
     "(%s%s)Z" % (STREAK_SERVICE, STRING), STREAKS),
    (STREAK_SERVICE, ("h0", "showsStreak"), "(%sZ)Z" % STRING,
     "(%s%sZ)Z" % (STREAK_SERVICE, STRING), STREAKS),

    # a sound pulled for copyright: the video stays and these four mute it
    (MUSIC, "available", "()Z", "(%s)Z" % MUSIC, SOUND),
    (MUSIC, "getMusicStatus", "()I", "(%s)I" % MUSIC, SOUND),
    (MUSIC, "isMuteShare", "()Z", "(%s)Z" % MUSIC, SOUND),
    (MUSIC, "getMuteType", "()I", "(%s)I" % MUSIC, SOUND),
]

# Statics of TikTok's own, which is how the flags are actually read: there is
# no receiver, so the instruction keeps its shape and only the class it lands
# in changes -- and the mod calls the original back by the same static.
MODEL_STATICS: List[Tuple[str, str, str, str, str]] = [
    (SETTINGS_MANAGER, (name, "flag"), "(%s)%s" % (args, kind),
     "(%s)%s" % (args, kind), FLAGS)
    for name, args, kind in AB_READERS
]

# owner, field, its type, ours, the class ours lives in. A field rather than a
# getter, so the read is an instruction of a different shape and becomes two.
FIELD_SOURCES: List[Tuple[str, str, str, str, str]] = [
    (VIDEO_CONTROL, "allowDownload", BOXED_BOOLEAN, "allowDownload", DOWNLOAD),
    # a slideshow is not a video and never goes near getDownloadAddr: its
    # images carry the stamp themselves, with the clean one beside them
    # every sticker the app touches, so the settings have something to offer as
    # the one to send. `currentImage()` reads like the right place and is not:
    # five call sites in the whole apk, none of them on the way to a screen.
    # This field is read in a couple of hundred, which is what drawing one
    # actually looks like.
    (STICKER_ITEM, "stickerBase", STICKER_BASE, "stickerBase", STREAKS),
    (PHOTO_IMAGE, "ownerWatermarkImage", URL_MODEL, "ownerWatermarkImage", DOWNLOAD),
    (PHOTO_IMAGE, "userWatermarkImage", URL_MODEL, "userWatermarkImage", DOWNLOAD),
]

# The pink TikTok is built around. Most of the places it is drawn hold it as a
# plain constant in the bytecode, so each of those becomes a call into the mod
# and the colour turns into something a person can change. The build counts
# what it found and stops if the answer is none: a colour picker that changes
# nothing is worse than no colour picker.
TIKTOK_PINK = 0xFFFE2C55

# Colours that arrive through the framework rather than as a constant. Same
# rewrite as the telephony calls: the receiver becomes the first argument.
#
# Reading a colour is only half of it. One that was never read -- computed,
# blended, carried in from somewhere the mod cannot see -- still has to be
# applied to something before it reaches the screen, and the places it can be
# applied are few and have real names. Those are the second half of the list,
# and they are what reaches the parts a resource table never could.
COLOUR_SOURCES: List[Tuple[str, str, str]] = [
    ("Landroid/content/res/Resources;", "getColor",
     "(I)I", "(Landroid/content/res/Resources;I)I"),
    ("Landroid/content/res/Resources;", "getColor",
     "(ILandroid/content/res/Resources$Theme;)I",
     "(Landroid/content/res/Resources;ILandroid/content/res/Resources$Theme;)I"),
    ("Landroid/content/res/TypedArray;", "getColor",
     "(II)I", "(Landroid/content/res/TypedArray;II)I"),
    ("Landroid/content/Context;", "getColor",
     "(I)I", "(Landroid/content/Context;I)I"),

    # where a colour is put to use: the brush, the shape, the tint, the text
    ("Landroid/graphics/Paint;", "setColor",
     "(I)V", "(Landroid/graphics/Paint;I)V"),
    ("Landroid/graphics/drawable/GradientDrawable;", "setColor",
     "(I)V", "(Landroid/graphics/drawable/GradientDrawable;I)V"),
    ("Landroid/widget/ImageView;", "setColorFilter",
     "(I)V", "(Landroid/widget/ImageView;I)V"),
    ("Landroid/widget/ImageView;", "setColorFilter",
     "(ILandroid/graphics/PorterDuff$Mode;)V",
     "(Landroid/widget/ImageView;ILandroid/graphics/PorterDuff$Mode;)V"),
    ("Landroid/widget/TextView;", "setTextColor",
     "(I)V", "(Landroid/widget/TextView;I)V"),
    ("Landroid/view/View;", "setBackgroundColor",
     "(I)V", "(Landroid/view/View;I)V"),
    # TikTok's own icon view, and a real name at that
    ("Lcom/bytedance/tux/icon/TuxIconView;", "setColor",
     "(I)V", "(Lcom/bytedance/tux/icon/TuxIconView;I)V"),
]

# A static of the framework's own: no receiver, so the call keeps its shape
# exactly and only the class it lands in changes.
COLOUR_STATICS: List[Tuple[str, str, str]] = [
    ("Landroid/content/res/ColorStateList;", "valueOf",
     "(I)Landroid/content/res/ColorStateList;"),
]

# method name -> (descriptor as TikTok calls it, descriptor of the static that
# replaces it -- the same, with the receiver moved into the arguments)
TARGETS: List[Tuple[str, str, str]] = [
    ("getSimCountryIso", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getNetworkCountryIso", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getSimOperator", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getNetworkOperator", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getSimOperatorName", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getNetworkOperatorName", "()Ljava/lang/String;", "(%s)Ljava/lang/String;" % TELEPHONY),
    ("getSimState", "()I", "(%s)I" % TELEPHONY),
    ("getSimState", "(I)I", "(%sI)I" % TELEPHONY),
    ("hasIccCard", "()Z", "(%s)Z" % TELEPHONY),
    ("isNetworkRoaming", "()Z", "(%s)Z" % TELEPHONY),
    ("getSimCarrierId", "()I", "(%s)I" % TELEPHONY),
]


# Methods that have to answer no, whatever they would have worked out.
#
# TikTok signs in with Google two ways: through Play Services, and through the
# browser with AppAuth and a custom-scheme redirect. It asks the first one
# whether it is available and only falls back to the second when it is not.
#
# For anything built here the Play Services way cannot work at all: Google
# checks the package name against the certificate's SHA-1, and the certificate
# is no longer TikTok's. Left alone it fails with a developer error and no way
# forward. So the provider that speaks to Play Services reports itself
# unavailable, and the app takes its own fallback -- the browser, which checks
# nothing but who receives the redirect.
#
# The class name is a real one, not an obfuscated one, which is what makes this
# safe to anchor on.
FORCED_FALSE: List[Tuple[str, str]] = [
    ("com/bytedance/lobby/google/GoogleAuth", "isAvailable()Z"),
]


def rules() -> List[Tuple[str, "re.Pattern[str]", str]]:
    out = []
    for name, original, replacement in TARGETS:
        pattern = re.compile(
            r"invoke-virtual(/range)? (\{[^}]*\}), %s->%s%s"
            % (re.escape(TELEPHONY), name, re.escape(original))
        )
        target = r"invoke-static\1 \2, %s->%s%s" % (REGION, name, replacement)
        out.append((name + original, pattern, target))
    return out


def accent_rules() -> List[Tuple[str, "re.Pattern[str]", str]]:
    """The pink, wherever the bytecode spells it out or asks for it."""
    out = []
    literal = "-0x%x" % ((1 << 32) - TIKTOK_PINK) if TIKTOK_PINK > 0x7FFFFFFF \
        else "0x%x" % TIKTOK_PINK
    # const vX, -0x1d3ab  ->  a call, and the answer in the same register
    out.append((
        "the pink itself",
        re.compile(r"^(\s*)const ([vp]\d+), %s$" % re.escape(literal), re.MULTILINE),
        r"\1invoke-static {}, %s->accent()I\n\n\1move-result \2" % ACCENT,
    ))
    for owner, name, original, replacement in COLOUR_SOURCES:
        out.append((
            "%s->%s%s" % (owner.split("/")[-1][:-1], name, original),
            re.compile(r"invoke-virtual(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), name, re.escape(original))),
            r"invoke-static\1 \2, %s->%s%s" % (ACCENT, name, replacement),
        ))
    for owner, name, signature in COLOUR_STATICS:
        out.append((
            "%s->%s" % (owner.split("/")[-1][:-1], name),
            re.compile(r"invoke-static(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), name, re.escape(signature))),
            r"invoke-static\1 \2, %s->%s%s" % (ACCENT, name, signature),
        ))
    return out


def model_rules() -> List[Tuple[str, "re.Pattern[str]", str]]:
    """Calls on TikTok's own models, answered by the mod instead."""
    out = []
    for owner, name, original, replacement, target in MODEL_SOURCES:
        # a pair when what the mod calls it differs from what TikTok does:
        # the app's obfuscated name on the way in, a readable one on the way out
        theirs, ours = name if isinstance(name, tuple) else (name, name)
        out.append((
            "%s->%s" % (owner.rsplit("/", 1)[-1][:-1], theirs),
            # an interface call is the same 35c instruction under another
            # mnemonic, and a service reached through one is still a receiver
            re.compile(r"invoke-(?:virtual|interface)(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), theirs, re.escape(original))),
            r"invoke-static\1 \2, %s->%s%s" % (target, ours, replacement),
        ))
    for owner, name, original, replacement, target in MODEL_STATICS:
        theirs, ours = name if isinstance(name, tuple) else (name, name)
        out.append((
            "%s->%s" % (owner.rsplit("/", 1)[-1][:-1], theirs),
            re.compile(r"invoke-static(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), theirs, re.escape(original))),
            r"invoke-static\1 \2, %s->%s%s" % (target, ours, replacement),
        ))
    for label, descriptor, ours, target in DISCOVERED_STATICS:
        found = FOUND.get(label)
        if found is None:
            continue
        owner, theirs = found
        out.append((
            label,
            re.compile(r"invoke-static(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), re.escape(theirs), re.escape(descriptor))),
            r"invoke-static\1 \2, %s->%s%s" % (target, ours, descriptor),
        ))
    for name, original, replacement, target in WILD_SOURCES:
        out.append((
            "%s (any owner)" % name,
            re.compile(r"invoke-(?:virtual|interface)(/range)? (\{[^}]*\}), L[^;]+;->%s%s"
                       % (name, re.escape(original))),
            r"invoke-static\1 \2, %s->%s%s" % (target, name, replacement),
        ))
    for owner, field, kind, name, target in FIELD_SOURCES:
        # iget-object vA, vB, Owner->field:Type
        #   -> invoke-static {vB}, Ours->name(Owner)Type ; move-result-object vA
        #
        # Which iget it is depends on what is being read: a long or a double is
        # two registers wide and has instructions of its own, and reading one
        # with the wrong instruction is not something the assembler forgives.
        if kind in ("J", "D"):
            read, took = "iget-wide", "move-result-wide"
        elif kind in ("Z", "B", "S", "C", "I", "F"):
            read, took = "iget", "move-result"
        else:
            read, took = "iget-object", "move-result-object"
        out.append((
            "%s.%s" % (owner.rsplit("/", 1)[-1][:-1], field),
            re.compile(r"^(\s*)%s ([vp]\d+), ([vp]\d+), %s->%s:%s$"
                       % (read, re.escape(owner), re.escape(field), re.escape(kind)),
                       re.MULTILINE),
            r"\1invoke-static {\3}, %s->%s(%s)%s\n\n\1%s \2"
            % (target, name, owner, kind, took),
        ))
    return out


def rewrite_models(root: str) -> Dict[str, int]:
    """Rewrite every call on TikTok's models, counting them by signature."""
    counts: Dict[str, int] = {}
    prepared = model_rules()
    owners = tuple(set([owner for owner, _n, _o, _r, _t in MODEL_SOURCES]
                       + [owner for owner, _n, _o, _r, _t in MODEL_STATICS]
                       + [owner for owner, _f, _k, _n, _t in FIELD_SOURCES]
                       # a rule with no owner of its own is recognised by the
                       # method it is looking for, or its file is never opened
                       + [name for name, _o, _r, _t in WILD_SOURCES]
                       # and one whose owner was found rather than written down
                       # is recognised by the owner that was found
                       + [FOUND[label][0] for label, _d, _o, _t in DISCOVERED_STATICS
                          if label in FOUND]))
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            if not any(owner in text for owner in owners):
                continue
            before = text
            for label, pattern, target in prepared:
                text, hits = pattern.subn(target, text)
                if hits:
                    counts[label] = counts.get(label, 0) + hits
            if text != before:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
    return counts


def anchored_rules() -> List[Tuple[str, str, "re.Pattern[str]", str]]:
    """Rules and the marker the class they belong in has to carry."""
    out = []
    for anchor, owner, name, original, replacement, target in ANCHORED_SOURCES:
        out.append((
            anchor,
            "%s->%s (in the class marked %s)" % (owner.rsplit("/", 1)[-1][:-1], name, anchor),
            re.compile(r"invoke-virtual(/range)? (\{[^}]*\}), %s->%s%s"
                       % (re.escape(owner), name, re.escape(original))),
            r"invoke-static\1 \2, %s->%s%s" % (target, name, replacement),
        ))
    return out


def rewrite_anchored(root: str) -> Dict[str, int]:
    """Rewrite calls inside the one class that carries the marker."""
    counts: Dict[str, int] = {}
    prepared = anchored_rules()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            before = text
            for anchor, label, pattern, target in prepared:
                if anchor not in text:
                    continue
                text, hits = pattern.subn(target, text)
                if hits:
                    counts[label] = counts.get(label, 0) + hits
            if text != before:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
    return counts


def carries_an_anchor(dex: bytes) -> bool:
    return any(anchor.encode() in dex for anchor, *_rest in ANCHORED_SOURCES)


def touches_a_model(dex: bytes) -> bool:
    """Whether a dex names one of TikTok's models and something we want on it."""
    for owner, name, _original, _replacement, _target in MODEL_SOURCES + MODEL_STATICS:
        theirs = name[0] if isinstance(name, tuple) else name
        if owner.encode() in dex and theirs.encode() in dex:
            return True
    for owner, field, _kind, _name, _target in FIELD_SOURCES:
        if owner.encode() in dex and field.encode() in dex:
            return True
    for name, _original, _replacement, _target in WILD_SOURCES:
        if name.encode() in dex:
            return True
    for label, _descriptor, _ours, _target in DISCOVERED_STATICS:
        found = FOUND.get(label)
        if found and found[0].encode() in dex and found[1].encode() in dex:
            return True
    return False


def reads_a_colour(dex: bytes) -> bool:
    """Whether a dex asks the framework for a colour.

    Most of TikTok's pink is not a constant at all: it is a colour resource,
    fetched by id, from code spread across most of the apk. Reaching it means
    opening every dex that asks -- which is most of them, and the reason a
    build takes a quarter of an hour rather than two minutes.
    """
    for owner, name, _original, _replacement in COLOUR_SOURCES:
        if owner.encode() in dex and name.encode() in dex:
            return True
    for owner, name, _signature in COLOUR_STATICS:
        if owner.encode() in dex and name.encode() in dex:
            return True
    return False


def holds_the_pink(dex: bytes) -> bool:
    """Whether a dex has the pink as a constant in an instruction.

    The four bytes of the colour turn up in string data and in tables too, and
    taking a dex apart costs half a minute -- so this looks for the instruction
    itself: opcode 0x14, `const vAA, #+BBBBBBBB`, the register, then the value.
    """
    needle = struct.pack("<I", TIKTOK_PINK)
    at = dex.find(needle)
    while at != -1:
        if at >= 2 and dex[at - 2] == 0x14:
            return True
        at = dex.find(needle, at + 1)
    return False


def rewrite_accent(root: str) -> Dict[str, int]:
    """Rewrite everywhere the pink is written down, counting as it goes."""
    counts: Dict[str, int] = {}
    prepared = accent_rules()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            before = text
            for label, pattern, target in prepared:
                text, hits = pattern.subn(target, text)
                if hits:
                    counts[label] = counts.get(label, 0) + hits
            if text != before:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
    return counts


def force_false(root: str) -> Dict[str, int]:
    """Rewrite the methods in FORCED_FALSE to `return false`, body and all."""
    counts: Dict[str, int] = {}
    for class_name, signature in FORCED_FALSE:
        path = os.path.join(root, *class_name.split("/")) + ".smali"
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        pattern = re.compile(
            r"^\.method ([^\n]*%s)\n.*?^\.end method$" % re.escape(signature),
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(text)
        if match is None:
            raise RuntimeError(
                "%s is in the apk but has no %s to rewrite -- the fallback this "
                "depends on has moved, and Google sign-in would be dead on arrival"
                % (class_name, signature)
            )
        stub = ".method %s\n    .registers 1\n\n    const/4 v0, 0x0\n\n    return v0\n.end method" % (
            match.group(1),
        )
        text = text[: match.start()] + stub + text[match.end():]
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        counts["%s->%s" % (class_name.rsplit("/", 1)[-1], signature)] = 1
    return counts


def interesting(dex: bytes, literals: Optional[Dict[str, str]] = None) -> bool:
    """A quick look at the raw dex before spending a minute on it.

    Every method a dex calls and every string it holds is in its string table,
    so a dex that never spells `TelephonyManager` cannot be calling one of
    these, and one that never spells an authority cannot be looking it up.
    """
    for old in (literals or {}):
        if old.encode() in dex:
            return True
    if (holds_the_pink(dex) or reads_a_colour(dex) or touches_a_model(dex)
            or carries_an_anchor(dex)):
        return True
    for class_name, _signature in FORCED_FALSE:
        if ("L%s;" % class_name).encode() in dex:
            return True
    if TELEPHONY.encode() not in dex:
        return False
    return any(name.encode() in dex for name, _o, _r in TARGETS)


def rewrite_literals(root: str, literals: Dict[str, str]) -> Dict[str, int]:
    """Swap whole string constants, for the authorities the manifest renamed.

    A provider authority renamed in the manifest and not in the code is an app
    that cannot find its own provider -- so if any of these strings turn out to
    be in the bytecode after all, they move with it.
    """
    counts: Dict[str, int] = {}
    if not literals:
        return counts
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            before = text
            for old, new in literals.items():
                needle = '"%s"' % old
                hits = text.count(needle)
                if hits:
                    text = text.replace(needle, '"%s"' % new)
                    counts[old] = counts.get(old, 0) + hits
            if text != before:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
    return counts


def rewrite_smali(root: str) -> Dict[str, int]:
    """Rewrite every call site under `root`, counting them by signature."""
    counts: Dict[str, int] = {}
    prepared = rules()
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".smali"):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
            if TELEPHONY not in text:
                continue
            before = text
            for label, pattern, target in prepared:
                text, hits = pattern.subn(target, text)
                if hits:
                    counts[label] = counts.get(label, 0) + hits
            if text != before:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text)
    return counts


class Smali:
    """baksmali and smali, from the one jar the build downloads."""

    def __init__(self, jar: str, api: int, jobs: int = 0, heap: str = "4g"):
        self.jar = jar
        self.api = api
        self.jobs = jobs or (os.cpu_count() or 2)
        self.heap = heap

    def _run(self, main: str, args: List[str]) -> None:
        command = ["java", "-Xmx" + self.heap, "-cp", self.jar, main] + args
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                "%s failed:\n%s\n%s" % (main.split(".")[-2], result.stdout, result.stderr)
            )

    def disassemble(self, dex_path: str, out_dir: str) -> None:
        self._run(
            "com.android.tools.smali.baksmali.Main",
            ["d", "-a", str(self.api), "-j", str(self.jobs), "-o", out_dir, dex_path],
        )

    def assemble(self, smali_dir: str, dex_path: str) -> None:
        self._run(
            "com.android.tools.smali.smali.Main",
            ["a", "-a", str(self.api), "-j", str(self.jobs), "-o", dex_path, smali_dir],
        )


def dex_format(dex: bytes) -> str:
    """The three digits after `dex\n`: 035, 038, 039 ..."""
    return dex[4:7].decode("ascii", "replace")


# --------------------------------------------------------- the landing sites
#
# Every rewrite above turns a call into the app's own code into a call into
# ours, and smali will assemble a call to a method that does not exist without
# a word: a dex may reference anything, and the runtime only goes looking when
# the instruction is reached. So a missing method is not a build failure, it is
# a NoSuchMethodError on whichever screen first draws that colour -- which is
# how `Accent.getColor(Context, int)`, rewritten at 33 dex files' worth of call
# sites and never written in Java, shipped once.


def rewrite_targets() -> List[str]:
    """Every static the rewrites point at, as `Lowner;->name(descriptor)`."""
    out = ["%s->accent()I" % ACCENT]
    for name, _original, replacement in TARGETS:
        out.append("%s->%s%s" % (REGION, name, replacement))
    for _owner, name, _original, replacement in COLOUR_SOURCES:
        out.append("%s->%s%s" % (ACCENT, name, replacement))
    for _owner, name, signature in COLOUR_STATICS:
        out.append("%s->%s%s" % (ACCENT, name, signature))
    for _owner, name, _original, replacement, target in MODEL_SOURCES + MODEL_STATICS:
        _theirs, ours = name if isinstance(name, tuple) else (name, name)
        out.append("%s->%s%s" % (target, ours, replacement))
    for owner, _field, kind, name, target in FIELD_SOURCES:
        out.append("%s->%s(%s)%s" % (target, name, owner, kind))
    for _anchor, _owner, name, _original, replacement, target in ANCHORED_SOURCES:
        out.append("%s->%s%s" % (target, name, replacement))
    for name, _original, replacement, target in WILD_SOURCES:
        out.append("%s->%s%s" % (target, name, replacement))
    for label, descriptor, ours, target in DISCOVERED_STATICS:
        if label in FOUND:
            out.append("%s->%s%s" % (target, ours, descriptor))
    return out


def _uleb(data: bytes, at: int) -> Tuple[int, int]:
    value = shift = 0
    while True:
        byte = data[at]
        at += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            return value, at


def defined_methods(dex: bytes) -> set:
    """The methods a dex actually defines, as `Lowner;->name(descriptor)`.

    Referenced methods are not enough: the whole point of the check is that a
    reference to a method nobody wrote is exactly what the build has to catch.
    So this walks the class definitions rather than the method table.
    """
    string_ids_off = struct.unpack_from("<I", dex, 60)[0]
    type_ids_off = struct.unpack_from("<I", dex, 68)[0]
    proto_ids_off = struct.unpack_from("<I", dex, 76)[0]
    method_ids_off = struct.unpack_from("<I", dex, 92)[0]
    class_defs_size, class_defs_off = struct.unpack_from("<2I", dex, 96)

    def string(index: int) -> str:
        at = struct.unpack_from("<I", dex, string_ids_off + 4 * index)[0]
        length, at = _uleb(dex, at)
        return dex[at:at + length].decode("utf-8", "replace")

    def type_name(index: int) -> str:
        return string(struct.unpack_from("<I", dex, type_ids_off + 4 * index)[0])

    def descriptor(index: int) -> str:
        _shorty, return_type, parameters = struct.unpack_from(
            "<3I", dex, proto_ids_off + 12 * index)
        arguments = ""
        if parameters:
            count = struct.unpack_from("<I", dex, parameters)[0]
            arguments = "".join(
                type_name(struct.unpack_from("<H", dex, parameters + 4 + 2 * i)[0])
                for i in range(count)
            )
        return "(%s)%s" % (arguments, type_name(return_type))

    def signature(index: int) -> str:
        owner, proto, name = struct.unpack_from("<HHI", dex, method_ids_off + 8 * index)
        return "%s->%s%s" % (type_name(owner), string(name), descriptor(proto))

    out = set()
    for i in range(class_defs_size):
        data_off = struct.unpack_from("<I", dex, class_defs_off + 32 * i + 24)[0]
        if not data_off:
            continue
        counts = []
        at = data_off
        for _ in range(4):  # static fields, instance fields, direct, virtual
            value, at = _uleb(dex, at)
            counts.append(value)
        for _ in range(counts[0] + counts[1]):
            _diff, at = _uleb(dex, at)
            _flags, at = _uleb(dex, at)
        for methods in (counts[2], counts[3]):
            index = 0
            for step in range(methods):
                diff, at = _uleb(dex, at)
                _flags, at = _uleb(dex, at)
                _code, at = _uleb(dex, at)
                index = diff if step == 0 else index + diff
                out.add(signature(index))
    return out


def find_statics(dexes: Dict[str, bytes]) -> Dict[str, Tuple[str, str]]:
    """Find each wanted static by its signature, across the whole apk.

    A descriptor is matched, not a name, so what comes back is whatever the
    obfuscator called it this release. Anything that matches in more than one
    class is dropped rather than guessed at: a rule that lands in the wrong
    place is worse than one that does not land at all.
    """
    wanted = {descriptor: label for label, descriptor, _ours, _target
              in DISCOVERED_STATICS}
    seen: Dict[str, set] = {label: set() for label in wanted.values()}

    for dex in dexes.values():
        for owner, name, descriptor in _static_methods(dex):
            label = wanted.get(descriptor)
            if label is not None:
                seen[label].add((owner, name))

    out: Dict[str, Tuple[str, str]] = {}
    for label, found in seen.items():
        if len(found) == 1:
            out[label] = next(iter(found))
    return out


def _static_methods(dex: bytes):
    """Every method the dex names, as (owner, name, descriptor)."""
    strings = struct.unpack_from("<I", dex, 60)[0]
    types = struct.unpack_from("<I", dex, 68)[0]
    protos = struct.unpack_from("<I", dex, 76)[0]
    count, methods = struct.unpack_from("<2I", dex, 88)

    def text(index: int) -> str:
        at = struct.unpack_from("<I", dex, strings + 4 * index)[0]
        size, at = _uleb(dex, at)
        return dex[at:at + size].decode("utf-8", "replace")

    def kind(index: int) -> str:
        return text(struct.unpack_from("<I", dex, types + 4 * index)[0])

    def shape(index: int) -> str:
        _shorty, ret, params = struct.unpack_from("<3I", dex, protos + 12 * index)
        taken = ""
        if params:
            how_many = struct.unpack_from("<I", dex, params)[0]
            taken = "".join(kind(struct.unpack_from("<H", dex, params + 4 + 2 * i)[0])
                            for i in range(how_many))
        return "(%s)%s" % (taken, kind(ret))

    for i in range(count):
        owner, proto, name = struct.unpack_from("<HHI", dex, methods + 8 * i)
        yield kind(owner), text(name), shape(proto)


def missing_targets(dex: bytes) -> List[str]:
    """Which of the rewrites' landing sites the mod's own dex does not define."""
    defined = defined_methods(dex)
    return [target for target in rewrite_targets() if target not in defined]


def patch(dex: bytes, name: str, smali: Smali, workspace: str,
          literals: Optional[Dict[str, str]] = None) -> Tuple[bytes, Dict[str, int]]:
    """Take one dex apart, rewrite what is in it, put it back together."""
    # a room of its own per dex, and never under a name something else uses:
    # the mod's own dex is called classes.dex too
    room = os.path.join(workspace, name.replace(".dex", ""))
    shutil.rmtree(room, ignore_errors=True)
    os.makedirs(room, exist_ok=True)

    dex_in = os.path.join(room, "in.dex")
    dex_out = os.path.join(room, "out.dex")
    with open(dex_in, "wb") as handle:
        handle.write(dex)

    smali.disassemble(dex_in, os.path.join(room, "smali"))
    counts = rewrite_smali(os.path.join(room, "smali"))
    counts.update(rewrite_literals(os.path.join(room, "smali"), literals or {}))
    counts.update(force_false(os.path.join(room, "smali")))
    counts.update(rewrite_accent(os.path.join(room, "smali")))
    counts.update(rewrite_models(os.path.join(room, "smali")))
    counts.update(rewrite_anchored(os.path.join(room, "smali")))
    if not counts:
        shutil.rmtree(room, ignore_errors=True)
        return dex, counts

    smali.assemble(os.path.join(room, "smali"), dex_out)
    with open(dex_out, "rb") as handle:
        patched = handle.read()
    shutil.rmtree(room, ignore_errors=True)

    if dex_format(patched) != dex_format(dex):
        raise RuntimeError(
            "%s came back as dex %s, it went in as dex %s -- an Android old "
            "enough to be in the apk's minSdk would refuse to load it"
            % (name, dex_format(patched), dex_format(dex))
        )
    return patched, counts


def next_dex_name(names: List[str]) -> str:
    """The name a new dex has to take to be loaded: the next in the run.

    The runtime loads classes.dex, then classes2.dex, and stops at the first
    number that is missing -- so an extra dex is only read if it continues the
    sequence.
    """
    used = set()
    for name in names:
        match = re.fullmatch(r"classes(\d*)\.dex", name)
        if match:
            used.add(int(match.group(1) or "1"))
    number = 2
    while number in used:
        number += 1
    return "classes%d.dex" % number
