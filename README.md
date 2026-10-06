# Podcast Novedades

Genera un .m3u con los últimos episodios de una lista de feeds RSS configurados en `feeds.yml`.

## Uso

1. Edita `feeds.yml` para añadir o quitar feeds.
2. Ajusta `limit` por feed o `default_limit` global.
3. El workflow de GitHub Actions se ejecuta cada día a las 04:00 UTC.
4. El archivo `novedades.m3u` se actualiza automáticamente.

## URL para escucharlos es:

https://raw.githubusercontent.com/gen8bit/podcast-novedades/main/novedades.m3u
