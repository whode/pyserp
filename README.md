# PySerp
PySerp is an asynchronous Python library for automated, flexibly configurable scraping and parsing of Search Engine Results Pages (SERPs).

## Purpose
Scraping search engine results is almost always necessary when the task is to automatically analyze these results, or to collect content from the links within them for any purpose.

Examples:
- Competitive analysis for keywords (SEO)
- Searching for and extracting any structured information from page content (phone numbers, emails, addresses, etc)
- Collecting page content to generate summaries (AI search)

## Key Features
This library:
- Is asynchronous by default for maximum efficiency
- Supports Google and Bing as search engines (more will be added in the future)
- Applies strict typing to results using `Pydantic`

## Installation

### From PyPI (Recommended)
Simply run:
```bash
pip install pyserp
```

### From Source (Development)
If you want to contribute or use the latest git version, download the source code:
```
git clone https://github.com/whode/pyserp
cd pyserp
```
Create a virtual environment (recommended):
```
python -m venv venv
```
And activate it

On Linux:
```bash
source venv/bin/activate
```
On Windows:
```cmd
venv\Scripts\activate
```
Install the library:
```
pip install -e .
```

## Usage
A simple, idiomatic usage example that demonstrates retrieving the top 10 search results from Google for a given query:
```python
import asyncio

from pyserp.providers import GoogleSearcherManager, GoogleSearchSessionsManager


async def main():
    query = "how to learn python"
    print("Searching for:", query, end="\n\n")

    cookies = {"NID": "YOUR_NID_COOKIE (Get it in your browser (but not Chrome): F12 -> Application -> Cookies)"}
    manager = GoogleSearchSessionsManager(cookies = cookies)
    async with GoogleSearcherManager(search_sessions_manager=manager) as searcher:
        search_top_result = await searcher.search_top(query=query,
                                                      limit=10,
                                                      include_page_errors=False)

        print("----- Results -----", end="\n\n")
        for page in search_top_result.pages:
            for result in page.results.organic:
                print(result.title, result.url, sep="\n", end="\n\n")


if __name__ == "__main__":
    asyncio.run(main())
```
The library offers much more than this. Full documentation will be added in the future.

## Development & Testing

Tests are included in the source repository only (not in the PyPI package).
To run tests, clone the repository:

```bash
git clone https://github.com/whode/pyserp.git
cd pyserp
pip install -U pytest
python -m pytest
```