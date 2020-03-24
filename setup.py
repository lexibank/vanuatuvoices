from setuptools import setup
import json


with open("metadata.json") as fp:
    metadata = json.load(fp)


setup(
    name='cldfbench_sndcmpvanuatu',
    description=metadata["title"],
    license=metadata.get("license", ""),
    url=metadata.get("url", ""),
    py_modules=['cldfbench_sndcmpvanuatu'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'sndcmpvanuatu=cldfbench_sndcmpvanuatu:Dataset',
        ],
        "cldfbench.commands": [
            "sndcmpvanuatu=sndcmpvanuatu_subcommands",
        ]
    },
    install_requires=[
        'cldfbench',
        'pylexibank>=2.4.0'
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
