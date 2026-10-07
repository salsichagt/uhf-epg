# UHF Favorites EPG

A compact XMLTV guide containing only the channels used by the UHF favorites playlist.

- Unique mapped EPG channels: **85**
- Sources: IPTV-EPG.org US, UK, Canada, Mexico and Australia guides
- Window: current programme + about 3 days ahead
- Automatic refresh: daily at about 04:17 Guatemala time
- Outputs: `epg.xml`, `epg.xml.gz`, and `status.json`

## UHF URL

After this repository is public and the first workflow run completes, use:

`https://raw.githubusercontent.com/salsichagt/uhf-epg/main/epg.xml`

Compressed alternative:

`https://raw.githubusercontent.com/salsichagt/uhf-epg/main/epg.xml.gz`

## Privacy

The original IPTV playlist is intentionally **not** stored in this repository because it contains private stream credentials. `channels.txt` contains only XMLTV/tvg IDs.
