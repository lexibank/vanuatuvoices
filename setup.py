from setuptools import setup
import json


with open("metadata.json") as fp:
    metadata = json.load(fp)


setup(
    name='cldfbench_sndcmpvanuatu',
    url=metadata.get("url", ""),
    py_modules=['cldfbench_sndcmpvanuatu'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'sndcmpvanuatu=cldfbench_sndcmpvanuatu:Dataset',
        ]
    },
    install_requires=[
        'cldfbench',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
