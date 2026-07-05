#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
constants module

Description:
  Global Constants
Author:
  惠达浪 <crazys@126.com>
Created:
  2025-06-16
"""

# Cache keys
ADMIN_ALL_MENU = 'admin_all_menu'

DEFAULT_APP_ICON = 'tabler-layout-dashboard'
# Auth menu icon constant
AUTH_APP_ICON = 'tabler-user-shield'

# custom sprite.svg file path
CUSTOM_SPRITE_FILE = 'svg/custom_sprite.svg'
PINMOK_SPRITE_FILE = 'admin/svg/sprite.svg'
PINMOK_ICON_PREFIX = "tabler-"

PINMOK_CONFIG_CACHE_TTL = 3600

# Language mapping: Django language code -> Hugerte RFC 5646 language value
# Only codes that need mapping are listed; unlisted codes fall back to English.
HUGERTE_LANG_MAP = {
    'ar': 'ar', 'az': 'az', 'be': 'be', 'ca': 'ca', 'cs': 'cs',
    'cy': 'cy', 'da': 'da', 'de': 'de', 'el': 'el', 'eo': 'eo',
    'es': 'es', 'et': 'et', 'eu': 'eu', 'fa': 'fa', 'fi': 'fi',
    'ga': 'ga', 'gl': 'gl', 'hi': 'hi', 'hr': 'hr', 'hy': 'hy',
    'id': 'id', 'it': 'it', 'ja': 'ja', 'kab': 'kab', 'kk': 'kk',
    'lt': 'lt', 'lv': 'lv', 'ne': 'ne', 'nl': 'nl', 'pl': 'pl',
    'ro': 'ro', 'ru': 'ru', 'sk': 'sk', 'sq': 'sq', 'sr': 'sr',
    'ta': 'ta', 'tg': 'tg', 'tr': 'tr', 'ug': 'ug', 'uk': 'uk',
    'uz': 'uz', 'vi': 'vi',
    # case / separator transform
    'zh-hans': 'zh-Hans',
    'zh-hant': 'zh-Hant',
    'pt-br': 'pt_BR',
    'es-mx': 'es_MX',
    # Django generic -> nearest hugerte regional
    'bg': 'bg_BG',
    'bn': 'bn_BD',
    'fr': 'fr_FR',
    'he': 'he_IL',
    'hu': 'hu_HU',
    'is': 'is_IS',
    'ka': 'ka_GE',
    'ko': 'ko_KR',
    'nb': 'nb_NO',
    'pt': 'pt_BR',
    'sl': 'sl_SI',
    'sv': 'sv_SE',
    'th': 'th_TH',
}

EXTERNAL_LINK_CACHE_KEY = 'pinmok_external_links'
