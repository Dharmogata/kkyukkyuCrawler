import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="kkyukkyuCrawler",
    version="1.0.1",
    author="eik4862",
    author_email="lkd1962@naver.com",
    description="law case crawling lib",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eik4862/kkyukkyuCrawler",
    project_urls={},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    python_requires=">=3.10",
    install_requires=[
        "PyPDF2>=3.0.1",
        "tqdm>=4.65",
        "beautifulsoup4>=4.12.2",
    ],
)
