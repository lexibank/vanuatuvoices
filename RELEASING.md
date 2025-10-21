# Releasing Vanuatu Voices

```shell
cldfbench lexibank.makecldf lexibank_vanuatuvoices.py --glottolog-version v5.2 --concepticon-version v3.4.0 --clts-version v2.3.0
pytest
```

```shell
cldfbench cldfreadme lexibank_vanuatuvoices.py
```

```shell
cldfbench cldfviz.map cldf --format png --height 40 --output map.png --markersize 30 --with-ocean --language-properties Island
```
