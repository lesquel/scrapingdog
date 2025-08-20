import os
import re
import sys
import json
import argparse
from typing import Optional

import requests

# Fallback (prefer environment variable SCRAPINGDOG_API_KEY)
DEFAULT_API_KEY = '5eaa61a6e562fc52fe763tr516e4653'
DEFAULT_PROFILE = 'Martinpdisalvo'


def normalize_profile_id(raw: str) -> str:
    """Accepts @handle, URL (https://x.com/<handle> or twitter.com), or numeric ID and returns the profile identifier.
    Examples:
      - "@coscu" -> "coscu"
      - "https://x.com/coscu" -> "coscu"
      - "https://twitter.com/coscu?s=20" -> "coscu"
      - "123456" -> "123456" (numeric id)
    """
    s = raw.strip()
    if s.startswith('@'):
        return s[1:]

    # URL forms
    m = re.match(r"https?://(x|twitter)\.com/([^/?#]+)", s, re.IGNORECASE)
    if m:
        return m.group(2)

    return s


def fetch_profile(api_key: str, profile_id: str) -> requests.Response:
    return requests.get(
        'https://api.scrapingdog.com/x/profile',
        params={'api_key': api_key, 'profileId': profile_id},
        timeout=30,
    )


def fetch_profile_multi(api_key: str, raw_profile: str, verbose: bool = False) -> requests.Response:
    """Try multiple endpoint/param variants to avoid 404 due to API changes.
    Returns the first successful (200) response or the last response if all fail.
    """
    handle = normalize_profile_id(raw_profile)
    handle_lc = handle.lower()
    is_numeric = handle.isdigit()

    endpoints = [
        'https://api.scrapingdog.com/x/profile',
        'https://api.scrapingdog.com/twitter/profile',
    ]

    params_list: list[dict] = []
    if is_numeric:
        for ep in endpoints:
            params_list.append({'endpoint': ep, 'userId': handle})
    else:
        # Try various param keys and value forms
        for ep in endpoints:
            for key in ('profileId', 'username', 'profile'):
                for val in (handle, f'@{handle}', handle_lc, f'@{handle_lc}'):
                    params_list.append({'endpoint': ep, key: val})
            # Also try passing full URL
            for url in (f'https://x.com/{handle}', f'https://twitter.com/{handle_lc}'):
                params_list.append({'endpoint': ep, 'url': url})

    last_resp: Optional[requests.Response] = None
    for entry in params_list:
        ep = entry.pop('endpoint')
        params = {'api_key': api_key}
        params.update(entry)
        if verbose:
            print(f"Probando {ep} con params: {params}")
        try:
            resp = requests.get(ep, params=params, timeout=30)
        except requests.RequestException as ex:
            last_resp = None
            if verbose:
                print(f"Error de red en {ep}: {ex}")
            continue
        last_resp = resp
        if resp.status_code == 200:
            # Validar que sea JSON utilizable; si no, seguir probando
            ctype = resp.headers.get('Content-Type', '')
            if 'json' in ctype.lower():
                try:
                    _ = resp.json()
                    return resp
                except Exception:
                    if verbose:
                        print('→ 200 pero respuesta no es JSON válido, continuando...')
            else:
                if verbose:
                    print(f"→ 200 pero Content-Type no JSON ({ctype}), continuando...")
        if verbose:
            snippet = resp.text[:200].replace('\n', ' ')
            print(f"→ {resp.status_code}: {snippet}")

    # If nothing succeeded, fall back to the default single call as a last attempt
    # Intento adicional: resolver ID numérico desde el handle y llamar con userId
    if not is_numeric:
        uid = resolve_user_id_public(handle_lc, verbose=verbose)
        if uid:
            if verbose:
                print(f"Resuelto userId público: {uid}, intentando con userId")
            for ep in endpoints:
                try:
                    resp = requests.get(ep, params={'api_key': api_key, 'userId': uid}, timeout=30)
                except requests.RequestException as ex:
                    last_resp = None
                    if verbose:
                        print(f"Error de red en {ep} con userId: {ex}")
                    continue
                last_resp = resp
                if resp.status_code == 200:
                    ctype = resp.headers.get('Content-Type', '')
                    if 'json' in ctype.lower():
                        try:
                            _ = resp.json()
                            return resp
                        except Exception:
                            if verbose:
                                print('→ 200 con userId pero JSON inválido, continuando...')
                    else:
                        if verbose:
                            print(f"→ 200 con userId pero Content-Type no JSON ({ctype})")
                if verbose:
                    snippet = resp.text[:200].replace('\n', ' ')
                    print(f"→ {resp.status_code} con userId: {snippet}")

    # Si nada funcionó, último intento directo
    try:
        if verbose:
            print("Intentando llamada por defecto a /x/profile con profileId")
        return fetch_profile(api_key, handle)
    except requests.RequestException:
        return last_resp  # type: ignore[return-value]


def resolve_user_id_public(handle: str, verbose: bool = False) -> Optional[str]:
    """Usa el endpoint público de widgets de Twitter para resolver el user id numérico.
    No requiere autenticación y suele devolver JSON con id/id_str.
    """
    url = 'https://cdn.syndication.twimg.com/widgets/followbutton/info.json'
    try:
        r = requests.get(url, params={'screen_names': handle}, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if r.status_code != 200:
            if verbose:
                print(f"Resolver ID → {r.status_code}: {r.text[:120]}")
            return None
        arr = r.json()
        if isinstance(arr, list) and arr:
            obj = arr[0]
            uid = obj.get('id_str') or (str(obj.get('id')) if obj.get('id') is not None else None)
            return uid
        return None
    except Exception as ex:
        if verbose:
            print(f"Resolver ID falló: {ex}")
        return None


def summarize_profile(data: dict) -> dict:
    """Return a small summary with the most important fields if present."""
    # Field names depend on provider; keep this defensive
    username = data.get('username') or data.get('screen_name') or data.get('handle')
    name = data.get('name') or data.get('full_name')
    followers = (
        data.get('followersCount')
        or data.get('followers')
        or data.get('followers_count')
    )
    following = (
        data.get('followingCount')
        or data.get('following')
        or data.get('friends_count')
    )
    verified = data.get('verified')
    description = data.get('description') or data.get('bio')
    location = data.get('location')
    url = data.get('url') or data.get('profile_url')
    user_id = data.get('id') or data.get('user_id')

    return {
        'username': username,
        'name': name,
        'user_id': user_id,
        'followers': followers,
        'following': following,
        'verified': verified,
        'location': location,
        'url': url,
        'description': description,
    }


def fetch_profile_public(handle: str, verbose: bool = False) -> Optional[dict]:
    """Obtiene info pública básica del perfil usando el endpoint de widgets.
    Devuelve un dict con campos similares a los de summarize_profile.
    """
    url = 'https://cdn.syndication.twimg.com/widgets/followbutton/info.json'
    try:
        r = requests.get(url, params={'screen_names': handle}, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
    except requests.RequestException as ex:
        if verbose:
            print(f"Fetch público falló: {ex}")
        return None
    if r.status_code != 200:
        if verbose:
            print(f"Fetch público → {r.status_code}: {r.text[:120]}")
        return None
    try:
        arr = r.json()
    except Exception:
        if verbose:
            print(f"Fetch público devolvió no-JSON: {r.text[:120]}")
        return None
    if not isinstance(arr, list) or not arr:
        return None
    obj = arr[0]
    mapped = {
        'username': obj.get('screen_name'),
        'name': obj.get('name'),
        'user_id': obj.get('id_str') or (str(obj.get('id')) if obj.get('id') is not None else None),
        'followers': obj.get('followers_count'),
        'following': obj.get('friends_count'),
        'verified': obj.get('verified'),
        'location': obj.get('location'),
        'url': f"https://x.com/{obj.get('screen_name')}" if obj.get('screen_name') else None,
        'description': obj.get('description'),
    }
    return mapped


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description='Fetch X/Twitter profile via ScrapingDog')
    parser.add_argument('profile', nargs='?', default=DEFAULT_PROFILE,
                        help='Handle (@user), URL (https://x.com/user) o ID numérico')
    parser.add_argument('--out', '-o', help='Guardar la respuesta JSON en un archivo')
    parser.add_argument('--verbose', '-v', action='store_true', help='Mostrar depuración de llamadas y parámetros')
    args = parser.parse_args(argv)

    api_key = os.getenv('SCRAPINGDOG_API_KEY', DEFAULT_API_KEY)
    if not api_key or api_key == 'YOUR_API_KEY_HERE':
        print('Falta la API key. Exporta SCRAPINGDOG_API_KEY o edita DEFAULT_API_KEY en el script.')
        return 1

    profile_id = normalize_profile_id(args.profile)
    if not profile_id:
        print('Perfil no válido. Proporciona un @handle, URL o ID.')
        return 1

    try:
        resp = fetch_profile_multi(api_key, profile_id, verbose=args.verbose)
    except requests.RequestException as ex:
        print(f'Error de red: {ex}')
        return 2

    if resp.status_code != 200:
        msg = None
        try:
            msg = resp.json().get('message')  # si viene JSON
        except Exception:
            pass
        error_text = msg or resp.text[:200]
        print(f'Error {resp.status_code}: {error_text}')
        # Fallback público si es user not found
        if 'user not found' in str(error_text).lower():
            handle = normalize_profile_id(profile_id).lower()
            alt = fetch_profile_public(handle, verbose=args.verbose)
            if alt:
                print('Perfil encontrado (fallback público):')
                print(f" - Usuario: @{alt.get('username') or handle}")
                if alt.get('name'):
                    print(f" - Nombre: {alt['name']}")
                if alt.get('user_id'):
                    print(f" - ID: {alt['user_id']}")
                if alt.get('followers') is not None:
                    print(f" - Seguidores: {alt['followers']}")
                if alt.get('following') is not None:
                    print(f" - Siguiendo: {alt['following']}")
                if alt.get('verified') is not None:
                    print(f" - Verificado: {alt['verified']}")
                if alt.get('url'):
                    print(f" - URL: {alt['url']}")
                if alt.get('location'):
                    print(f" - Ubicación: {alt['location']}")
                return 0
        return resp.status_code

    try:
        data = resp.json()
    except Exception:
        ctype = resp.headers.get('Content-Type', '')
        print(f"Respuesta 200 pero no es JSON válido (Content-Type: {ctype}). Fragmento: {resp.text[:200]}")
        return 3
    summary = summarize_profile(data)

    # Mostrar un resumen legible
    print('Perfil encontrado:')
    print(f" - Usuario: @{summary.get('username') or profile_id}")
    if summary.get('name'):
        print(f" - Nombre: {summary['name']}")
    if summary.get('user_id'):
        print(f" - ID: {summary['user_id']}")
    if summary.get('followers') is not None:
        print(f" - Seguidores: {summary['followers']}")
    if summary.get('following') is not None:
        print(f" - Siguiendo: {summary['following']}")
    if summary.get('verified') is not None:
        print(f" - Verificado: {summary['verified']}")
    if summary.get('url'):
        print(f" - URL: {summary['url']}")
    if summary.get('location'):
        print(f" - Ubicación: {summary['location']}")

    if args.out:
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Respuesta completa guardada en: {args.out}")

    return 0


if __name__ == '__main__':
    sys.exit(main())