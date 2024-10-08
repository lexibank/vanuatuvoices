from setuptools import setup
import json


with open("metadata.json", encoding="utf-8") as fp:
    metadata = json.load(fp)


setup(
    name='lexibank_vanuatuvoices',
    description=metadata["title"],
    license=metadata.get("license", ""),
    url=metadata.get("url", ""),
    py_modules=['lexibank_vanuatuvoices'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'lexibank.dataset': [
            'vanuatuvoices=lexibank_vanuatuvoices:Dataset',
        ],
        "cldfbench.commands": [
            "vanuatuvoices=vanuatuvoices_subcommands",
        ]
    },
    install_requires=[
        'pylexibank>=3.4.0',
        'cldfbench>=1.13.0',
        'zenodoclient>=0.5.0',
        'csvw>=3.1.3',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
