import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="word-mover-grammar",
    version="0.0.2",
    author="David Dale",
    author_email="dale.david@mail.ru",
    description="A constituency grammar parser with support of morphology and word embeddings",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/avidale/word-mover-grammar",
    packages=setuptools.find_packages(),
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
        'pyyaml'
    ],
    extras_require={
        'rumorph': ['pymorphy2[fast]', 'pymorphy2-dicts-ru'],
    }
)
