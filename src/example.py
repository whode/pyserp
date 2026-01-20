import asyncio

from pyserp.providers import GoogleSearcherManager, GoogleSearchSessionsManager


async def main():
    query = "how to learn java"
    print("Searching for:", query, end="\n\n")

    cookies = {"NID": "YOUR_NID_COOKIE"}
    manager = GoogleSearchSessionsManager(cookies = cookies)
    async with GoogleSearcherManager(search_sessions_manager=manager) as searcher:
        search_top_result = await searcher.search_top(query=query,
                                                      limit=10,
                                                      include_page_errors=False)

        print("----- Results -----", end="\n\n")
        for page in search_top_result.pages:
            for result in page.results.organic:
                print(result.title, result.url, sep="\n", end="\n\n")
    await manager.close()

if __name__ == "__main__":
    asyncio.run(main())
